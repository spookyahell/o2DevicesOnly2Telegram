import requests, json, time, sys
from os.path import isfile
from telegram import Bot
from telegram.error import TimedOut
from copy import copy


hw_only = 'https://www.o2online.de/e-shop/rest/catalog/o2shop/privatkunden/ratenzahlung/default/__not-specified__/__not-specified__/__not-specified__?hwOnly=true'

class Bot(Bot):
	def send_message2(self, *args, **kwargs):
		#~ print(args,  kwargs)
		try:
			self.send_message(*args, **kwargs)
		except TimedOut:
			print('Sending the message timed out unfortunately. Trying again in 10 seconds...')
			time.sleep(10)
			return send_message2(*args, **kwargs)

bot = Bot('482467545:AAGfcWivbAWVpolN6kT_7SX30s8v3piNWCg')
chat = -1001376659104

device_message_ids = {}


def save_mids():
	with open('hw_mids.json', 'w', encoding = 'utf-8-sig') as dmids:
		dmids.write(json.dumps(device_message_ids, indent = 2))
	print('device message ids saved!')

if isfile('hw_mids.json'):
	with open('hw_mids.json', encoding = 'utf-8-sig') as dmids:
		device_message_ids = json.loads(dmids.read())

def get_mid(urlName):
	for key in device_message_ids:
		if key == urlName:
			return device_message_ids[key]

def gen_device_message(item):
	x = item['urlName']
	img_url = item['imageUrl']
	item_name = item['description']
	buy_url = item['detailWwwAbsoluteCall']['constantPayload']['link']['uri']
	monthly_price = item['price']['monthlyPrice']
	total_price = item['price']['totalPrice']
	total_price_rf = f'{total_price:0.02f}'.replace('.',',')
	monthly_price_rf = f'{monthly_price:0.02f}'.replace('.',',')
	return f'[{item_name}]({img_url})\nBuy [here]({buy_url}) (hardware only)\n\nPrice: *{total_price_rf}€* ({monthly_price_rf}€ x 24 monthly installments)'
			
def notifyChange(property, old_val, new_val, url_name):
	mid = get_mid(url_name)
	if old_val  == '':
		old_val = '[emtpy value]'
	if new_val == '':
		new_val = '[emtpy value]'
	bot.send_message2(chat, f'The property *{property}* of the referenced device has changed from _{old_val}_ to _{new_val}_.', parse_mode = 'Markdown',  reply_to_message_id = mid)
	time.sleep(30)

def addDevice(item):
	message_text = gen_device_message(item)
	message = bot.send_message(chat, message_text, parse_mode = 'Markdown')
	mid = message.message_id
	device_message_ids[item['urlName']] = mid
	save_mids()
	time.sleep(30)

while True:
	print('Fetching devices from o2 now...')
	r = requests.get(hw_only)
	try:
		hw_data = r.json()
	except json.decoder.JSONDecodeError:
		# Error - but why?
		if '<title>404 - Seite nicht gefunden</title>' in r.text:
			print('That\'s weird, we got a 404 response (ironically with "200 OK"status code), so... trying again...')
			time.sleep(5)
			r = requests.get(hw_only)
			hw_data = r.json()
			
	hw_items = hw_data['hardware']

	if isfile('hw_data.json'):
		with open('hw_data.json', encoding = 'utf-8-sig') as hw_data_file:
			old_data = json.loads(hw_data_file.read())
			
		old_data_items = old_data['hardware']
		
		
		def find_in_data(title):
			for item in hw_items:
				if item['urlName'] == title:
					return item
			return None
			
		def find_in_old_data(title):
			for item in old_data_items:
				if item['urlName'] == title:
					return item
			return None
		
		if old_data_items == hw_data:
			print('Nothing changed!')
		else:
			for idx, item in enumerate(old_data_items):
				dev_name = item['description']
				dev_uname = item['urlName']
				item_new = find_in_data(dev_uname)
				if item_new is not None:
					if 'indexBySortingName' in item:		
						del item['indexBySortingName']
					if 'indexBySortingName' in item_new:
						del item_new['indexBySortingName']
					
					keys_to_remove = []
					for key, value in item.items():
						if value:
							if 'javax.net.ssl.SSLException' in value:
								keys_to_remove.append(key)
								#~ del item[key]
								#~ del item_new[key]
						
					for key, value in item_new.items():
						if value:
							if 'javax.net.ssl.SSLException' in value:
								keys_to_remove.append(key)
									#~ del item[key]
					for key in keys_to_remove:
						if key in item:
							del item[key]
						if key in item_new:
							del item_new[key]
					if ('marketingHint' in item) and ('marketingHint' in item_new):
						if item['marketingHint'] != item_new['marketingHint']:
							notifyChange('marketingHint', item['marketingHint'], item_new['marketingHint'], dev_uname)
							item['marketingHint'] = copy(item_new['marketingHint'])
					try:
						if 'imageUrl' in item:
							del item['imageUrl']
							del item['imageUrlSmall']
						if 'imageUrl' in item_new:
							del item_new['imageUrl']
							del item_new['imageUrlSmall']
					except KeyError:
						print('WTF?! imageUrl bot not imageUrlSmall?!')
						jso = {'new':item_new,'old':item}
						with open('change.json', 'w') as f:
							f.write(json.dumps(jso, indent = 2))
						sys.exit(2)
					if item_new != item:
						if item['description'] == item_new['description']:
							bot.send_message(chat, f'It looks like something from this item has changed: {dev_name}')
							jso = {'new':item_new,'old':item}
							with open('change.json', 'w') as f:
								f.write(json.dumps(jso, indent = 2))
							exit()
							sleep(30)
				else:
					bot.send_message(chat, 'It looks like this item has been removed.', reply_to_message_id = get_mid(item['urlName']))
					
			for idx, item in enumerate(hw_items):
				dev_name = item['description']
				dev_uname = item['urlName']
				item_old = find_in_old_data(dev_uname)
				if item_old is None:
					addDevice(item)
			
	if not isfile('hwonly_initialized'):
		for idx, item in enumerate(hw_items):
			addDevice(item)
			
		with open('hwonly_initialized','w') as init_file:
			init_file.close()
			

	with open('hw_data.json', 'w', encoding = 'utf-8-sig') as hw_data_file:
		hw_data_file.write(json.dumps(hw_data, indent = 2))
	
	print('Sleeping for 5m now...')
	message = bot.edit_message_text(	time.strftime('\[Zuletzt gemeldet: `%Y-%m-%d %H:%M:%S`]')+
	'\n✅ Alles überprüft.\nKeine neuen Infos verfügbar.', chat, 86, parse_mode = 'Markdown', timeout = 30)
	#~ print(message)
	time.sleep(300)