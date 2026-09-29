import json
with open('final_fixed2.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

with open('prices_check.txt', 'w', encoding='utf-8') as out:
    for item in data:
        platform = item.get('platform', '')
        price = item.get('price_eur', 0)
        title = item.get('title', '')[:60]
        out.write(f'{platform} | {price} EUR | {title}\n')

print('Done')
