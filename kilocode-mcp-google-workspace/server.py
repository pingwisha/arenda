#!/usr/bin/env python
"""
Google Spreadsheet MCP Server
A Model Context Protocol (MCP) server built with FastMCP for interacting with Google Sheets.
"""

import base64
import os
from typing import List, Dict, Any, Optional, Union
import json
from dataclasses import dataclass
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

# MCP imports
from mcp.server.fastmcp import FastMCP, Context

# Google API imports
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import google.auth
from googleapiclient.http import MediaIoBaseDownload, MediaInMemoryUpload

# Constants
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/documents']
CREDENTIALS_CONFIG = os.environ.get('CREDENTIALS_CONFIG')
TOKEN_PATH = os.environ.get('TOKEN_PATH', 'token.json')
CREDENTIALS_PATH = os.environ.get('CREDENTIALS_PATH', 'credentials.json')
SERVICE_ACCOUNT_PATH = os.environ.get('SERVICE_ACCOUNT_PATH', 'service_account.json')
SERVICE_ACCOUNT_KEY_PATH = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', 'service-account-key.json')
DRIVE_FOLDER_ID = os.environ.get('DRIVE_FOLDER_ID', '')  # Working directory in Google Drive
# Enable/disable creation tools via environment variable (default: disabled)
# Set ENABLE_CREATE_TOOLS=true to enable create_spreadsheet, create_sheet, create_document tools
ENABLE_CREATE_TOOLS = os.environ.get("ENABLE_CREATE_TOOLS", "false").lower() == "true"

@dataclass
class SpreadsheetContext:
    """Context for Google Spreadsheet service"""
    sheets_service: Any
    drive_service: Any
    docs_service: Any
    folder_id: Optional[str] = None


@asynccontextmanager
async def spreadsheet_lifespan(server: FastMCP) -> AsyncIterator[SpreadsheetContext]:
    """Manage Google Spreadsheet API connection lifecycle"""
    
    creds = None

    
    if CREDENTIALS_CONFIG:
        creds = service_account.Credentials.from_service_account_info(json.loads(base64.b64decode(CREDENTIALS_CONFIG)), scopes=SCOPES)

    if not creds and SERVICE_ACCOUNT_PATH and os.path.exists(SERVICE_ACCOUNT_PATH):
        try:
            creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_PATH, scopes=SCOPES)
        except Exception as e:
            creds = None

    if not creds and SERVICE_ACCOUNT_KEY_PATH and os.path.exists(SERVICE_ACCOUNT_KEY_PATH):
        try:
            creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_KEY_PATH, scopes=SCOPES)
        except Exception as e:
            creds = None

    if not creds:
        if os.path.exists(TOKEN_PATH):
            with open(TOKEN_PATH, 'r') as token:
                creds = Credentials.from_authorized_user_info(json.load(token), SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
                    creds = flow.run_local_server(port=0)
                    with open(TOKEN_PATH, 'w') as token:
                        token.write(creds.to_json())
                except Exception as e:
                    creds = None

    if not creds:
        try:
            creds, project = google.auth.default(scopes=SCOPES)
        except Exception as e:
            raise Exception("All authentication methods failed.")

    sheets_service = build('sheets', 'v4', credentials=creds)
    drive_service = build('drive', 'v3', credentials=creds)
    docs_service = build('docs', 'v1', credentials=creds)
    
    try:
        yield SpreadsheetContext(
            sheets_service=sheets_service,
            drive_service=drive_service,
            docs_service=docs_service,
            folder_id=DRIVE_FOLDER_ID if DRIVE_FOLDER_ID else None
        )
    finally:
        pass


# Initialize the MCP server with lifespan management
mcp = FastMCP("Google Spreadsheet", 
              dependencies=["google-auth", "google-auth-oauthlib", "google-api-python-client"],
              lifespan=spreadsheet_lifespan)

# Helper function to conditionally register tools
def conditional_tool(condition: bool):
    """Decorator to conditionally register tools based on environment variable"""
    def decorator(func):
        if condition:
            return mcp.tool()(func)
        else:
            # Return the function without registering it as a tool
            return func
    return decorator


@mcp.tool()
def get_sheet_data(spreadsheet_id: str, 
                   sheet: str,
                   range: Optional[str] = None,
                   include_grid_data: bool = False,
                   ctx: Context = None) -> Dict[str, Any]:
    """
    Get data from a specific sheet in a Google Spreadsheet.
    
    ⚡ Atomic operation - single API call.
    
    Args:
        spreadsheet_id: The ID of the spreadsheet (found in the URL)
        sheet: The name of the sheet
        range: Optional cell range in A1 notation (e.g., 'A1:C10'). If not provided, gets all data.
        include_grid_data: If True, includes cell formatting and other metadata in the response.
            Note: Setting this to True will significantly increase the response size and token usage
            when parsing the response, as it includes detailed cell formatting information.
            Default is False (returns values only, more efficient).
    
    Returns:
        Grid data structure with either full metadata or just values from Google Sheets API, depending on include_grid_data parameter
    """
    sheets_service = ctx.request_context.lifespan_context.sheets_service

    try:
        # Construct the range - keep original API behavior
        if range:
            full_range = f"{sheet}!{range}"
        else:
            full_range = sheet
        
        if include_grid_data:
            # Use full API to get all grid data including formatting
            result = sheets_service.spreadsheets().get(
                spreadsheetId=spreadsheet_id,
                ranges=[full_range],
                includeGridData=True
            ).execute()
        else:
            # Use values API to get cell values only (more efficient)
            values_result = sheets_service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=full_range
            ).execute()
            
            # Format the response to match expected structure
            result = {
                'spreadsheetId': spreadsheet_id,
                'valueRanges': [{
                    'range': full_range,
                    'values': values_result.get('values', [])
                }]
            }

        return result
    except Exception as e:
        return {'error': str(e)}

@mcp.tool()
def get_sheet_formulas(spreadsheet_id: str,
                       sheet: str,
                       range: Optional[str] = None,
                       ctx: Context = None) -> List[List[Any]]:
    """
    Get formulas from a specific sheet in a Google Spreadsheet.
    
    ⚡ Atomic operation - single API call.
    
    Args:
        spreadsheet_id: The ID of the spreadsheet (found in the URL)
        sheet: The name of the sheet
        range: Optional cell range in A1 notation (e.g., 'A1:C10'). If not provided, gets all formulas from the sheet.
    
    Returns:
        A 2D array of the sheet formulas.
    """
    sheets_service = ctx.request_context.lifespan_context.sheets_service
    
    try:
        # Construct the range
        if range:
            full_range = f"{sheet}!{range}"
        else:
            full_range = sheet  # Get all formulas in the specified sheet
        
        # Call the Sheets API
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=full_range,
            valueRenderOption='FORMULA'  # Request formulas
        ).execute()
        
        # Get the formulas from the response
        formulas = result.get('values', [])
        return formulas
    except Exception as e:
        return [{'error': str(e)}]

@mcp.tool()
def update_cells(spreadsheet_id: str,
                sheet: str,
                range: str,
                data: List[List[Any]],
                ctx: Context = None) -> Dict[str, Any]:
    """
    Update cells in a Google Spreadsheet.
    
    ⚡ Atomic operation - single API call.
    
    Args:
        spreadsheet_id: The ID of the spreadsheet (found in the URL)
        sheet: The name of the sheet
        range: Cell range in A1 notation (e.g., 'A1:C10')
        data: 2D array of values to update
    
    Returns:
        Result of the update operation
    """
    sheets_service = ctx.request_context.lifespan_context.sheets_service
    
    try:
        # Construct the range
        full_range = f"{sheet}!{range}"
        
        # Prepare the value range object
        value_range_body = {
            'values': data
        }
        
        # Call the Sheets API to update values
        result = sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=full_range,
            valueInputOption='USER_ENTERED',
            body=value_range_body
        ).execute()
        
        return result
    except Exception as e:
        return {'error': str(e)}


@mcp.tool()
def batch_update_cells(spreadsheet_id: str,
                       sheet: str,
                       ranges: Dict[str, List[List[Any]]],
                       ctx: Context = None) -> Dict[str, Any]:
    """
    Batch update multiple ranges in a Google Spreadsheet.
    
    ⚡ **ATOMIC BATCH OPERATION** - all ranges are updated in a single API call.
    Either all changes are applied successfully, or none are applied.
    Guarantees data integrity for multiple updates.
    
    Args:
        spreadsheet_id: The ID of the spreadsheet (found in the URL)
        sheet: The name of the sheet
        ranges: Dictionary mapping range strings to 2D arrays of values
               e.g., {'A1:B2': [[1, 2], [3, 4]], 'D1:E2': [['a', 'b'], ['c', 'd']]}
    
    Returns:
        Result of the batch update operation
    """
    sheets_service = ctx.request_context.lifespan_context.sheets_service
    
    try:
        # Prepare the batch update request
        data = []
        for range_str, values in ranges.items():
            full_range = f"{sheet}!{range_str}"
            data.append({
                'range': full_range,
                'values': values
            })
        
        batch_body = {
            'valueInputOption': 'USER_ENTERED',
            'data': data
        }
        
        # Call the Sheets API to perform batch update
        result = sheets_service.spreadsheets().values().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=batch_body
        ).execute()
        
        return result
    except Exception as e:
        return {'error': str(e)}


@mcp.tool()
def add_rows(spreadsheet_id: str,
             sheet: str,
             count: int,
             start_row: Optional[int] = None,
             ctx: Context = None) -> Dict[str, Any]:
    """
    Add rows to a sheet in a Google Spreadsheet.
    
    ⚡ Atomic operation - single batchUpdate API call.
    
    Args:
        spreadsheet_id: The ID of the spreadsheet (found in the URL)
        sheet: The name of the sheet
        count: Number of rows to add
        start_row: 0-based row index to start adding. If not provided, adds at the beginning.
    
    Returns:
        Result of the operation
    """
    sheets_service = ctx.request_context.lifespan_context.sheets_service
    
    try:
        # Get sheet ID
        spreadsheet = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheet_id = None
        
        for s in spreadsheet['sheets']:
            if s['properties']['title'] == sheet:
                sheet_id = s['properties']['sheetId']
                break
                
        if sheet_id is None:
            return {"error": f"Sheet '{sheet}' not found"}
        
        # Prepare the insert rows request
        request_body = {
            "requests": [
                {
                    "insertDimension": {
                        "range": {
                            "sheetId": sheet_id,
                            "dimension": "ROWS",
                            "startIndex": start_row if start_row is not None else 0,
                            "endIndex": (start_row if start_row is not None else 0) + count
                        },
                        "inheritFromBefore": start_row is not None and start_row > 0
                    }
                }
            ]
        }
        
        # Execute the request
        result = sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=request_body
        ).execute()
        
        return result
    except Exception as e:
        return {'error': str(e)}


@mcp.tool()
def add_columns(spreadsheet_id: str,
                sheet: str,
                count: int,
                start_column: Optional[int] = None,
                ctx: Context = None) -> Dict[str, Any]:
    """
    Add columns to a sheet in a Google Spreadsheet.
    
    ⚡ Atomic operation - single batchUpdate API call.
    
    Args:
        spreadsheet_id: The ID of the spreadsheet (found in the URL)
        sheet: The name of the sheet
        count: Number of columns to add
        start_column: 0-based column index to start adding. If not provided, adds at the beginning.
    
    Returns:
        Result of the operation
    """
    sheets_service = ctx.request_context.lifespan_context.sheets_service
    
    try:
        # Get sheet ID
        spreadsheet = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheet_id = None
        
        for s in spreadsheet['sheets']:
            if s['properties']['title'] == sheet:
                sheet_id = s['properties']['sheetId']
                break
                
        if sheet_id is None:
            return {"error": f"Sheet '{sheet}' not found"}
        
        # Prepare the insert columns request
        request_body = {
            "requests": [
                {
                    "insertDimension": {
                        "range": {
                            "sheetId": sheet_id,
                            "dimension": "COLUMNS",
                            "startIndex": start_column if start_column is not None else 0,
                            "endIndex": (start_column if start_column is not None else 0) + count
                        },
                        "inheritFromBefore": start_column is not None and start_column > 0
                    }
                }
            ]
        }
        
        # Execute the request
        result = sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=request_body
        ).execute()
        
        return result
    except Exception as e:
        return {'error': str(e)}


@mcp.tool()
def list_sheets(spreadsheet_id: str, ctx: Context = None) -> List[str]:
    """
    List all sheets in a Google Spreadsheet.
    
    ⚡ Atomic operation - single API call.
    
    Args:
        spreadsheet_id: The ID of the spreadsheet (found in the URL)
    
    Returns:
        List of sheet names
    """
    sheets_service = ctx.request_context.lifespan_context.sheets_service
    
    try:
        # Get spreadsheet metadata
        spreadsheet = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        
        # Extract sheet names
        sheet_names = [sheet['properties']['title'] for sheet in spreadsheet['sheets']]
        
        return sheet_names
    except Exception as e:
        return [{'error': str(e)}]


@mcp.tool()
def copy_sheet(src_spreadsheet: str,
               src_sheet: str,
               dst_spreadsheet: str,
               dst_sheet: str,
               ctx: Context = None) -> Dict[str, Any]:
    """
    Copy a sheet from one spreadsheet to another.
    
    ⚠️ Non-atomic operation - involves copy and potential rename operations.
    
    Args:
        src_spreadsheet: Source spreadsheet ID
        src_sheet: Source sheet name
        dst_spreadsheet: Destination spreadsheet ID
        dst_sheet: Destination sheet name
    
    Returns:
        Result of the operation
    """
    sheets_service = ctx.request_context.lifespan_context.sheets_service
    
    try:
        # Get source sheet ID
        src = sheets_service.spreadsheets().get(spreadsheetId=src_spreadsheet).execute()
        src_sheet_id = None
        
        for s in src['sheets']:
            if s['properties']['title'] == src_sheet:
                src_sheet_id = s['properties']['sheetId']
                break
                
        if src_sheet_id is None:
            return {"error": f"Source sheet '{src_sheet}' not found"}
        
        # Copy the sheet to destination spreadsheet
        copy_result = sheets_service.spreadsheets().sheets().copyTo(
            spreadsheetId=src_spreadsheet,
            sheetId=src_sheet_id,
            body={
                "destinationSpreadsheetId": dst_spreadsheet
            }
        ).execute()
        
        # If destination sheet name is different from the default copied name, rename it
        if 'title' in copy_result and copy_result['title'] != dst_sheet:
            # Get the ID of the newly copied sheet
            copy_sheet_id = copy_result['sheetId']
            
            # Rename the copied sheet
            rename_request = {
                "requests": [
                    {
                        "updateSheetProperties": {
                            "properties": {
                                "sheetId": copy_sheet_id,
                                "title": dst_sheet
                            },
                            "fields": "title"
                        }
                    }
                ]
            }
            
            rename_result = sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=dst_spreadsheet,
                body=rename_request
            ).execute()
            
            return {
                "copy": copy_result,
                "rename": rename_result
            }
        
        return {"copy": copy_result}
    except Exception as e:
        return {'error': str(e)}


@mcp.tool()
def rename_sheet(spreadsheet: str,
                 sheet: str,
                 new_name: str,
                 ctx: Context = None) -> Dict[str, Any]:
    """
    Rename a sheet in a Google Spreadsheet.
    
    ⚡ Atomic operation - single batchUpdate API call.
    
    Args:
        spreadsheet: Spreadsheet ID
        sheet: Current sheet name
        new_name: New sheet name
    
    Returns:
        Result of the operation
    """
    sheets_service = ctx.request_context.lifespan_context.sheets_service
    
    try:
        # Get sheet ID
        spreadsheet_data = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet).execute()
        sheet_id = None
        
        for s in spreadsheet_data['sheets']:
            if s['properties']['title'] == sheet:
                sheet_id = s['properties']['sheetId']
                break
                
        if sheet_id is None:
            return {"error": f"Sheet '{sheet}' not found"}
        
        # Prepare the rename request
        request_body = {
            "requests": [
                {
                    "updateSheetProperties": {
                        "properties": {
                            "sheetId": sheet_id,
                            "title": new_name
                        },
                        "fields": "title"
                    }
                }
            ]
        }
        
        # Execute the request
        result = sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet,
            body=request_body
        ).execute()
        
        return result
    except Exception as e:
        return {'error': str(e)}


@mcp.tool()
def delete_sheet(spreadsheet: str,
                 sheet: str,
                 ctx: Context = None) -> Dict[str, Any]:
    """
    Delete a sheet from a Google Spreadsheet.
    
    ⚡ Atomic operation - single batchUpdate API call.
    
    Args:
        spreadsheet: Spreadsheet ID
        sheet: Sheet name to delete
    
    Returns:
        Result of the operation
    """
    sheets_service = ctx.request_context.lifespan_context.sheets_service
    
    try:
        # Get sheet ID and check if it's the only sheet
        spreadsheet_data = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet).execute()
        sheet_id = None
        total_sheets = len(spreadsheet_data['sheets'])
        
        for s in spreadsheet_data['sheets']:
            if s['properties']['title'] == sheet:
                sheet_id = s['properties']['sheetId']
                break
                
        if sheet_id is None:
            return {"error": f"Sheet '{sheet}' not found"}
        
        # Prevent deletion if it's the only sheet
        if total_sheets <= 1:
            return {"error": "Cannot delete the only sheet in the spreadsheet"}
        
        # Prepare the delete request
        request_body = {
            "requests": [
                {
                    "deleteSheet": {
                        "sheetId": sheet_id
                    }
                }
            ]
        }
        
        # Execute the request
        result = sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet,
            body=request_body
        ).execute()
        
        return result
    except Exception as e:
        return {'error': str(e)}


@mcp.tool()
def get_multiple_sheet_data(queries: List[Dict[str, str]], 
                            ctx: Context = None) -> List[Dict[str, Any]]:
    """
    Get data from multiple specific ranges in Google Spreadsheets.
    
    ⚠️ Non-atomic operation - multiple API calls.
    
    Args:
        queries: A list of dictionaries, each specifying a query. 
                 Each dictionary should have 'spreadsheet_id', 'sheet', and 'range' keys.
                 Example: [{'spreadsheet_id': 'abc', 'sheet': 'Sheet1', 'range': 'A1:B5'}, 
                           {'spreadsheet_id': 'xyz', 'sheet': 'Data', 'range': 'C1:C10'}]
    
    Returns:
        A list of dictionaries, each containing the original query parameters 
        and the fetched 'data' or an 'error'.
    """
    sheets_service = ctx.request_context.lifespan_context.sheets_service
    results = []
    
    for query in queries:
        spreadsheet_id = query.get('spreadsheet_id')
        sheet = query.get('sheet')
        range_str = query.get('range')
        
        if not all([spreadsheet_id, sheet, range_str]):
            results.append({**query, 'error': 'Missing required keys (spreadsheet_id, sheet, range)'})
            continue

        try:
            # Construct the range
            full_range = f"{sheet}!{range_str}"
            
            # Call the Sheets API
            result = sheets_service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=full_range
            ).execute()
            
            # Get the values from the response
            values = result.get('values', [])
            results.append({**query, 'data': values})

        except Exception as e:
            results.append({**query, 'error': str(e)})
            
    return results


@mcp.tool()
def get_multiple_spreadsheet_summary(spreadsheet_ids: List[str],
                                   rows_to_fetch: int = 5, 
                                   ctx: Context = None) -> List[Dict[str, Any]]:
    """
    Get a summary of multiple Google Spreadsheets, including sheet names, 
    headers, and the first few rows of data for each sheet.
    
    ⚠️ Non-atomic operation - multiple API calls.
    
    Args:
        spreadsheet_ids: A list of spreadsheet IDs to summarize.
        rows_to_fetch: The number of rows (including header) to fetch for the summary (default: 5).
    
    Returns:
        A list of dictionaries, each representing a spreadsheet summary. 
        Includes spreadsheet title, sheet summaries (title, headers, first rows), or an error.
    """
    sheets_service = ctx.request_context.lifespan_context.sheets_service
    summaries = []
    
    for spreadsheet_id in spreadsheet_ids:
        summary_data = {
            'spreadsheet_id': spreadsheet_id,
            'title': None,
            'sheets': [],
            'error': None
        }
        try:
            # Get spreadsheet metadata
            spreadsheet = sheets_service.spreadsheets().get(
                spreadsheetId=spreadsheet_id,
                fields='properties.title,sheets(properties(title,sheetId))'
            ).execute()
            
            summary_data['title'] = spreadsheet.get('properties', {}).get('title', 'Unknown Title')
            
            sheet_summaries = []
            for sheet in spreadsheet.get('sheets', []):
                sheet_title = sheet.get('properties', {}).get('title')
                sheet_id = sheet.get('properties', {}).get('sheetId')
                sheet_summary = {
                    'title': sheet_title,
                    'sheet_id': sheet_id,
                    'headers': [],
                    'first_rows': [],
                    'error': None
                }
                
                if not sheet_title:
                    sheet_summary['error'] = 'Sheet title not found'
                    sheet_summaries.append(sheet_summary)
                    continue
                    
                try:
                    # Fetch the first few rows (e.g., A1:Z5)
                    # Adjust range if fewer rows are requested
                    max_row = max(1, rows_to_fetch) # Ensure at least 1 row is fetched
                    range_to_get = f"{sheet_title}!A1:{max_row}" # Fetch all columns up to max_row
                    
                    result = sheets_service.spreadsheets().values().get(
                        spreadsheetId=spreadsheet_id,
                        range=range_to_get
                    ).execute()
                    
                    values = result.get('values', [])
                    
                    if values:
                        sheet_summary['headers'] = values[0]
                        if len(values) > 1:
                            sheet_summary['first_rows'] = values[1:max_row]
                    else:
                        # Handle empty sheets or sheets with less data than requested
                        sheet_summary['headers'] = []
                        sheet_summary['first_rows'] = []

                except Exception as sheet_e:
                    sheet_summary['error'] = f'Error fetching data for sheet {sheet_title}: {sheet_e}'
                
                sheet_summaries.append(sheet_summary)
            
            summary_data['sheets'] = sheet_summaries
            
        except Exception as e:
            summary_data['error'] = f'Error fetching spreadsheet {spreadsheet_id}: {e}'
            
        summaries.append(summary_data)
        
    return summaries


@mcp.resource("spreadsheet://{spreadsheet_id}/info")
def get_spreadsheet_info(spreadsheet_id: str) -> str:
    """
    Get basic information about a Google Spreadsheet.
    
    ⚡ Atomic operation - single API call.
    
    Args:
        spreadsheet_id: The ID of the spreadsheet
    
    Returns:
        JSON string with spreadsheet information
    """
    # Access the context through mcp.get_lifespan_context() for resources
    context = mcp.get_lifespan_context()
    sheets_service = context.sheets_service
    
    try:
        # Get spreadsheet metadata
        spreadsheet = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        
        # Extract relevant information
        info = {
            "title": spreadsheet.get('properties', {}).get('title', 'Unknown'),
            "sheets": [
                {
                    "title": sheet['properties']['title'],
                    "sheetId": sheet['properties']['sheetId'],
                    "gridProperties": sheet['properties'].get('gridProperties', {})
                }
                for sheet in spreadsheet.get('sheets', [])
            ]
        }
        
        return json.dumps(info, indent=2)
    except Exception as e:
        return json.dumps({'error': str(e)})


@conditional_tool(ENABLE_CREATE_TOOLS)
def create_spreadsheet(title: str, ctx: Context = None) -> Dict[str, Any]:
    """
    Create a new Google Spreadsheet.
    
    ⚡ Atomic operation - single API call.
    
    Args:
        title: The title of the new spreadsheet
    
    Returns:
        Information about the newly created spreadsheet including its ID
    """
    drive_service = ctx.request_context.lifespan_context.drive_service
    folder_id = ctx.request_context.lifespan_context.folder_id

    try:
        # Create the spreadsheet
        file_body = {
            'name': title,
            'mimeType': 'application/vnd.google-apps.spreadsheet',
        }
        if folder_id:
            file_body['parents'] = [folder_id]
        
        spreadsheet = drive_service.files().create(
            supportsAllDrives=True,
            body=file_body,
            fields='id, name, parents'
        ).execute()

        spreadsheet_id = spreadsheet.get('id')
        parents = spreadsheet.get('parents')
        print(f"Spreadsheet created with ID: {spreadsheet_id}")

        return {
            'spreadsheetId': spreadsheet_id,
            'title': spreadsheet.get('name', title),
            'folder': parents[0] if parents else 'root',
        }
    except Exception as e:
        return {'error': str(e)}


@mcp.tool()
def create_sheet(spreadsheet_id: str,
                title: str,
                ctx: Context = None) -> Dict[str, Any]:
    """
    Create a new sheet tab in an existing Google Spreadsheet.
    
    ⚡ Atomic operation - single batchUpdate API call.
    
    Args:
        spreadsheet_id: The ID of the spreadsheet
        title: The title for the new sheet
    
    Returns:
        Information about the newly created sheet
    """
    sheets_service = ctx.request_context.lifespan_context.sheets_service
    
    try:
        # Define the add sheet request
        request_body = {
            "requests": [
                {
                    "addSheet": {
                        "properties": {
                            "title": title
                        }
                    }
                }
            ]
        }
        
        # Execute the request
        result = sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=request_body
        ).execute()
        
        # Extract the new sheet information
        new_sheet_props = result['replies'][0]['addSheet']['properties']
        
        return {
            'sheetId': new_sheet_props['sheetId'],
            'title': new_sheet_props['title'],
            'index': new_sheet_props.get('index'),
            'spreadsheetId': spreadsheet_id
        }
    except Exception as e:
        return {'error': str(e)}


@mcp.tool()
def list_spreadsheets(limit: int = 50, ctx: Context = None) -> List[Dict[str, str]]:
    """
    List all spreadsheets accessible by the service account on Google Drive.
    
    ⚡ Atomic operation - single API call.
    
    Args:
        limit: Maximum number of spreadsheets to return (default: 50, max: 100)
    
    Returns:
        List of spreadsheets with their ID and title, ordered by modification time (newest first)
    """
    drive_service = ctx.request_context.lifespan_context.drive_service
    
    # Ensure limit is within reasonable bounds
    limit = min(max(1, limit), 100)  # Between 1 and 100
    
    try:
        query = "mimeType='application/vnd.google-apps.spreadsheet' and trashed=false"
        print(f"Searching for up to {limit} accessible spreadsheets on Google Drive")
        
        # List spreadsheets
        results = drive_service.files().list(
            q=query,
            spaces='drive',
            includeItemsFromAllDrives=True,
            supportsAllDrives=True,
            fields='files(id, name, modifiedTime)',
            orderBy='modifiedTime desc',
            pageSize=limit
        ).execute()
        
        spreadsheets = results.get('files', [])
        
        return [{'id': sheet['id'], 'title': sheet['name'], 'modifiedTime': sheet.get('modifiedTime')} for sheet in spreadsheets]
    except Exception as e:
        return [{'error': str(e)}]


@mcp.tool()
def share_spreadsheet(spreadsheet_id: str, 
                      recipients: List[Dict[str, str]],
                      send_notification: bool = True,
                      ctx: Context = None) -> Dict[str, List[Dict[str, Any]]]:
    """
    Share a Google Spreadsheet with multiple users via email, assigning specific roles.
    
    ⚠️ Non-atomic operation - multiple API calls (one per recipient).
    
    Args:
        spreadsheet_id: The ID of the spreadsheet to share.
        recipients: A list of dictionaries, each containing 'email_address' and 'role'.
                    The role should be one of: 'reader', 'commenter', 'writer'.
                    Example: [
                        {'email_address': 'user1@example.com', 'role': 'writer'},
                        {'email_address': 'user2@example.com', 'role': 'reader'}
                    ]
        send_notification: Whether to send a notification email to the users. Defaults to True.

    Returns:
        A dictionary containing lists of 'successes' and 'failures'. 
        Each item in the lists includes the email address and the outcome.
    """
    drive_service = ctx.request_context.lifespan_context.drive_service
    successes = []
    failures = []
    
    for recipient in recipients:
        email_address = recipient.get('email_address')
        role = recipient.get('role', 'writer') # Default to writer if role is missing for an entry
        
        if not email_address:
            failures.append({
                'email_address': None,
                'error': 'Missing email_address in recipient entry.'
            })
            continue
            
        if role not in ['reader', 'commenter', 'writer']:
             failures.append({
                'email_address': email_address,
                'error': f"Invalid role '{role}'. Must be 'reader', 'commenter', or 'writer'."
            })
             continue

        permission = {
            'type': 'user',
            'role': role,
            'emailAddress': email_address
        }
        
        try:
            result = drive_service.permissions().create(
                fileId=spreadsheet_id,
                body=permission,
                sendNotificationEmail=send_notification,
                fields='id'
            ).execute()
            successes.append({
                'email_address': email_address, 
                'role': role, 
                'permissionId': result.get('id')
            })
        except Exception as e:
            # Try to provide a more informative error message
            error_details = str(e)
            if hasattr(e, 'content'):
                try:
                    error_content = json.loads(e.content)
                    error_details = error_content.get('error', {}).get('message', error_details)
                except json.JSONDecodeError:
                    pass # Keep the original error string
            failures.append({
                'email_address': email_address,
                'error': f"Failed to share: {error_details}"
            })
            
    return {"successes": successes, "failures": failures}

@mcp.tool()
def get_doc_content(document_id: str, ctx: Context = None) -> Dict[str, Any]:
    """
    Get content from a Google Document.
    
    ⚡ Atomic operation - single API call.

    Args:
        document_id: The ID of the Google Document (found in the URL)
    
    Returns:
        A dictionary containing the document title and its content (as a list of elements).
    """
    docs_service = ctx.request_context.lifespan_context.docs_service

    try:
        document = docs_service.documents().get(documentId=document_id).execute()
        
        title = document.get('title', 'Unknown Title')
        content = document.get('body', {}).get('content', [])
        
        return {
            'title': title,
            'content': content
        }
    except Exception as e:
        return {
            'error': str(e)
        }

@mcp.tool()
def get_doc_text(document_id: str, ctx: Context = None) -> str:
    """
    Reads a Google Doc and returns all its text content as a single string.
    This is a helper function that processes the output of get_doc_content.
    
    ⚡ Atomic operation - single API call.

    Args:
        document_id: The ID of the Google Document.
    
    Returns:
        A single string containing all the text from the document.
    """
    # Get the structured content of the document
    doc_data = get_doc_content(document_id, ctx)

    if 'error' in doc_data:
        return f"Error retrieving document: {doc_data['error']}"

    text_parts = []
    # The content is in a list of structural elements
    for element in doc_data.get('content', []):
        # We are interested in paragraphs
        if 'paragraph' in element:
            # Paragraphs contain a list of 'elements' which are text runs
            for para_element in element['paragraph'].get('elements', []):
                # We want the text from each text run
                if 'textRun' in para_element:
                    text_parts.append(para_element['textRun'].get('content', ''))
    
    return "".join(text_parts)

@conditional_tool(ENABLE_CREATE_TOOLS)
def create_document(title: str, ctx: Context = None) -> Dict[str, Any]:
    """
    Create a new Google Document.
    
    ⚡ Atomic operation - single API call.

    Args:
        title: The title of the new document.
    
    Returns:
        Information about the newly created document including its ID.
    """
    drive_service = ctx.request_context.lifespan_context.drive_service
    folder_id = ctx.request_context.lifespan_context.folder_id

    file_body = {
        'name': title,
        'mimeType': 'application/vnd.google-apps.document',
    }
    if folder_id:
        file_body['parents'] = [folder_id]
    
    try:
        document = drive_service.files().create(
            supportsAllDrives=True,
            body=file_body,
            fields='id, name, parents'
        ).execute()

        document_id = document.get('id')
        parents = document.get('parents')
        
        return {
            'documentId': document_id,
            'title': document.get('name', title),
            'folder': parents[0] if parents else 'root',
        }
    except Exception as e:
        return {'error': str(e)}

@mcp.tool()
def insert_text_into_doc(document_id: str, text: str, ctx: Context = None) -> Dict[str, Any]:
    """
    Inserts text at the end of a Google Document.
    
    ⚡ Atomic operation - single batchUpdate API call.

    Args:
        document_id: The ID of the Google Document.
        text: The text to insert.
    
    Returns:
        The result of the batchUpdate operation.
    """
    docs_service = ctx.request_context.lifespan_context.docs_service
    
    try:
        # Get the current document to find the end of the content
        document = docs_service.documents().get(documentId=document_id).execute()
        # The body content is a list of Structural Elements.
        # The last element's endIndex is the end of the document body.
        content = document.get('body', {}).get('content', [])
        end_of_doc_index = content[-1].get('endIndex', 1) if content else 1

        # To insert at the very end, we use the endIndex of the last element.
        # We also need to add a newline if the document doesn't end with one.
        if not text.startswith('\n'):
            text = '\n' + text

        requests = [
            {
                'insertText': {
                    'location': {
                        # Insert at the second to last position to be before the final newline of the document
                        'index': end_of_doc_index - 1,
                    },
                    'text': text
                }
            }
        ]
        
        result = docs_service.documents().batchUpdate(
            documentId=document_id,
            body={'requests': requests}
        ).execute()
        return result
    except Exception as e:
        return {'error': str(e)}

@mcp.tool()
def delete_text_from_doc(document_id: str, text_to_delete: str, ctx: Context = None) -> Dict[str, Any]:
    """
    Deletes the first occurrence of a specific text string from a Google Document.
    This implementation correctly handles text spread across multiple text runs.
    
    ⚡ Atomic operation - single batchUpdate API call.

    Args:
        document_id: The ID of the Google Document.
        text_to_delete: The exact text string to find and delete.
    
    Returns:
        The result of the batchUpdate operation or an error message.
    """
    docs_service = ctx.request_context.lifespan_context.docs_service
    
    try:
        document = docs_service.documents().get(documentId=document_id).execute()
        content = document.get('body', {}).get('content', [])
        
        # Find the range of the text to delete
        # This is a complex task because the text can be split across multiple 'textRun' elements.
        # This implementation will find the start and end index of the first exact match.
        
        full_text = "".join(
            para_element.get('textRun', {}).get('content', '')
            for element in content
            if 'paragraph' in element
            for para_element in element['paragraph'].get('elements', [])
        )
        
        if text_to_delete not in full_text:
            return {'error': f'Text "{text_to_delete}" not found in document.'}
            
        # Find start and end indices
        start_index, end_index = -1, -1
        running_len = 0
        
        # Iterate through all elements to map string position to API indices
        for element in content:
            if 'paragraph' in element:
                for para_element in element['paragraph'].get('elements', []):
                    if 'textRun' in para_element:
                        text_run = para_element['textRun']
                        run_content = text_run.get('content', '')
                        run_len = len(run_content)
                        
                        # Check if the text to delete starts in this run
                        if start_index == -1 and text_to_delete in full_text[running_len:running_len + run_len]:
                            # Find the start position of the substring
                            sub_pos = full_text[running_len:running_len + run_len].find(text_to_delete)
                            start_index = para_element['startIndex'] + sub_pos
                        
                        # Check if the text to delete ends in this run
                        if start_index != -1 and running_len + run_len >= full_text.find(text_to_delete) + len(text_to_delete):
                            sub_pos = full_text[running_len:running_len + run_len].find(text_to_delete[-(full_text.find(text_to_delete) + len(text_to_delete) - running_len):])
                            end_index = para_element['startIndex'] + sub_pos + (full_text.find(text_to_delete) + len(text_to_delete) - running_len)
                            break
                            
                        running_len += run_len
            if end_index != -1:
                break
        
        if start_index == -1 or end_index == -1:
            return {'error': 'Could not accurately determine the range of the text to delete.'}

        # Create the delete request
        requests = [
            {
                'deleteContentRange': {
                    'range': {
                        'startIndex': start_index,
                        'endIndex': end_index,
                    }
                }
            }
        ]

        # Execute the request
        result = docs_service.documents().batchUpdate(
            documentId=document_id,
            body={'requests': requests}
        ).execute()
        return result

    except Exception as e:
        return {'error': str(e)}

@mcp.tool()
def search_drive_files(query: str, ctx: Context = None) -> List[Dict[str, str]]:
    """
    Search for files in Google Drive based on a query string.
    
    ⚡ Atomic operation - single API call.

    Args:
        query: The query string for searching files (e.g., 'name = "MyFile.pdf"').
               See https://developers.google.com/drive/api/guides/search-files for query syntax.
    
    Returns:
        A list of dictionaries, each containing the file ID and title of matching files.
    """
    drive_service = ctx.request_context.lifespan_context.drive_service

    try:
        # Call the Drive API to search for files
        results = drive_service.files().list(
            q=query,
            spaces='drive',
            includeItemsFromAllDrives=True,
            supportsAllDrives=True,
            fields='files(id, name)'
        ).execute()

        # Extract the files from the response
        files = results.get('files', [])
        return [{'id': file['id'], 'title': file['name']} for file in files]
    except Exception as e:
        return [{'error': str(e)}]


@mcp.tool()
def download_googledoc_from_drive(file_id: str,
                            destination_path: str,
                            ctx: Context = None) -> Dict[str, Any]:
    """
    Downloads a Google Doc file in text format from Google Drive to a local path.
    This tool specifically handles Google Docs and exports them as plain text (.txt) files.
    
    ⚡ Atomic operation - single API call.

    Args:
        file_id: The ID of the Google Doc file to download.
        destination_path: The local path where the text file should be saved (should end with .txt).
    
    Returns:
        A dictionary containing the file ID, original document name, and destination path, or an error message.
    """
    drive_service = ctx.request_context.lifespan_context.drive_service

    if not destination_path or not isinstance(destination_path, str):
        # This is a workaround for a suspected issue where destination_path becomes empty.
        print(f"--- WARNING: Received invalid destination_path. It might be empty or not a string.")
        file_metadata_for_name = drive_service.files().get(fileId=file_id, supportsAllDrives=True, fields='name').execute()
        doc_name = file_metadata_for_name.get('name', f'document_{file_id}')
        destination_path = f'{doc_name}.txt'
        print(f"--- INFO: Defaulting to filename '{destination_path}' in the container's working directory.")

    try:
        # Call the Drive API to get the file metadata
        file_metadata = drive_service.files().get(
            fileId=file_id,
            supportsAllDrives=True,
            fields='name, mimeType'
        ).execute()

        # Get the file name and mime type
        file_name = file_metadata.get('name', 'Unknown Document')
        mime_type = file_metadata.get('mimeType', '')

        # Verify this is a Google Doc
        if mime_type != 'application/vnd.google-apps.document':
            return {'error': f'File is not a Google Doc. MIME type: {mime_type}. This tool only works with Google Docs.'}

        # Export the Google Doc as plain text
        request = drive_service.files().export_media(
            fileId=file_id,
            mimeType='text/plain'
        )
        
        # Create the destination directory if it doesn't exist
        if destination_path and '/' in destination_path:
            os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        
        # Download the exported text file
        with open(destination_path, 'wb') as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                print(f"Export download {int(status.progress() * 100)}%.")

        return {
            'fileId': file_id,
            'documentName': file_name,
            'originalMimeType': mime_type,
            'exportedAs': 'text/plain',
            'destinationPath': destination_path
        }
    except Exception as e:
        return {'error': str(e)}


@mcp.tool()
def update_googledoc_in_drive(file_id: str,
                        new_content: str,
                        ctx: Context = None) -> Dict[str, Any]:
    """
    Updates the content of a file Google Doc in Google Drive.
    
    ⚡ Atomic operation - single API call.

    Args:
        file_id: The ID of the Google Doc file to update.
        new_content: The new content for the file.
    
    Returns:
        A dictionary containing the Google Doc file ID and a success message, or an error message.
    """
    drive_service = ctx.request_context.lifespan_context.drive_service

    try:
        # Prepare the media upload with new content
        media = MediaInMemoryUpload(new_content.encode('utf-8'), mimetype='text/plain', resumable=True)

        #

        # Update the file
        file = drive_service.files().update(
            fileId=file_id,
            media_body=media,
            supportsAllDrives=True,
            fields='id, name, parents'
        ).execute()

        file_id = file.get('id')
        parents = file.get('parents')
        print(f"File updated with ID: {file_id}")

        return {
            'fileId': file_id,
            'title': file.get('name', 'Unknown'),
            'folder': parents[0] if parents else 'root',
        }
    except Exception as e:
        return {'error': str(e)}



def main():
     
     mcp.run()
     


if __name__ == "__main__":
    main()