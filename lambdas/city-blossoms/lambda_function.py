import bs4
import requests
import json
import csv
import boto3

bucket = 'aimeeb-datasets-public'
is_local = False

def fetch_page(options):
  url = options['url']
  html_doc = requests.get(url).content
  return html_doc

# Given a beautiful soup object, return a list of events on that page
def handle_city_blossoms_page(soup):
  events = soup.find_all('div', {'class': ' summary-item summary-item-record-type-event sqs-gallery-design-autogrid-slide summary-item-has-thumbnail summary-item-has-author summary-item-has-comments-enabled summary-item-has-location'})
  event_output = []

  for e in events:
    #couldn't find lat_long data
    latLong = None

    url_end = e.find('div', class_ = 'summary-thumbnail-outer-container').find('a').get('href')
    event_url = 'http://cityblossoms.org' + url_end
    
    #get specific event page and parse through
    event_page = requests.get(event_url)
    soup_event_page = bs4.BeautifulSoup(event_page.content, 'html.parser')
    main_area = soup_event_page.find('div',class_= 'sqs-events-collection-item').find('article', class_ = 'eventitem').find('div', class_ = 'eventitem-column-meta')
    title = main_area.find('h1', class_ = 'eventitem-title').text
    venueName = main_area.find('span', class_ = 'eventitem-meta-address-line eventitem-meta-address-line--title').text
    venueAddress_1 = main_area.find_all('span', class_ = 'eventitem-meta-address-line')[1].text
    venueAddress_2 =  main_area.find_all('span', class_ = 'eventitem-meta-address-line')[2].text

    states = {'D.C.', 'DC', 'District of Columbia', 'VA', 'Virginia', 'Maryland', 'MD'}

    #only pick events that are situated in DMV region
    if any(state in venueAddress_2 for state in states):
        venueAddress = venueAddress_1 + ' ' + venueAddress_2
    else:
        continue

    description = soup.find('div', class_ = 'sqs-block-content').text

    try: 
        start_date = main_area.find_all('time', class_ = 'event-date')[0].text
        start_time = main_area.find_all('time', class_ = 'event-time-12hr')[0].text
        end_date = main_area.find_all('time', class_ = 'event-date')[1].text
        end_time = main_area.find_all('time', class_ = 'event-time-12hr')[1].text

    except:
        start_date = main_area.find('time', class_ = 'event-date').text
        start_time = main_area.find('time', class_ = 'event-time-12hr-start').text
        end_time = main_area.find('time', class_ = 'event-time-12hr-end').text
        end_date = start_date

    event_data = {
      'website': event_url,
      'startDate': start_date,
      'startTime': start_time,
      'endDate': end_date,
      'endTime': end_time,
      'venueName': venueName,
      'venueAddress': venueAddress,
      'latitude': None,
      'longitude': None,
    }
    
    event_output.append(event_data)

  return event_output



def handler(event, context):
  url = event['url']
  source_name = event['source_name']
  page = fetch_page({'url': url})
  soup = bs4.BeautifulSoup(page, 'html.parser')
  event_output = handle_city_blossoms_page(soup)
  filename = '{0}-results.csv'.format(source_name)
  if not is_local:
    with open('/tmp/{0}'.format(filename), mode = 'w') as f:
      writer = csv.DictWriter(f, fieldnames = event_output[0].keys())
      writer.writeheader()
      [writer.writerow(event) for event in event_output]
    s3 = boto3.resource('s3')
    s3.meta.client.upload_file(
      '/tmp/{0}'.format(filename),
      bucket,
      'capital-nature/{0}'.format(filename)
    )  
  return json.dumps(event_output, indent=2)

#For local testing
event = {
  'url': 'http://cityblossoms.org/calendar/',
  'source_name': 'city-blossoms'
}
is_local = True
print(handler(event, {}))

