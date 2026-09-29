from googleapiclient.discovery import build
from google.oauth2 import service_account

creds = service_account.Credentials.from_service_account_file(
    r'C:\Users\maria\OneDrive\Документы\квартиры\kilocode-mcp-google-workspace\service-account-key.json',
    scopes=['https://www.googleapis.com/auth/spreadsheets']
)
service = build('sheets', 'v4', credentials=creds)
spreadsheet_id = '1yXzUII6pZ9rg57C0c7gefl57z88uz1_mKlNBy8Nu4g0'
sheet_name = 'Проверка_подключения'

metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
titles = [sh['properties']['title'] for sh in metadata.get('sheets', [])]
print('existing_sheets=', titles)

if sheet_name not in titles:
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={
            'requests': [
                {
                    'addSheet': {
                        'properties': {
                            'title': sheet_name,
                            'sheetType': 'GRID',
                            'gridProperties': {'rowCount': 50, 'columnCount': 10}
                        }
                    }
                }
            ]
        }
    ).execute()
    print('sheet_created')

service.spreadsheets().values().append(
    spreadsheetId=spreadsheet_id,
    range=f'{sheet_name}!A1',
    valueInputOption='RAW',
    insertDataOption='INSERT_ROWS',
    body={'values': [['ok', '2026-09-21', 'google-sheets-api']]}
).execute()
print('write_ok')
