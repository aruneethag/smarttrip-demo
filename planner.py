"""Deterministic demo planning and server-enforced business rules."""
import copy
import re
import uuid
from datetime import date, datetime, timedelta, timezone
from schema import validate_schema

CURRENCIES = {'USD': 2, 'EUR': 2, 'GBP': 2, 'INR': 2, 'JPY': 0, 'CAD': 2, 'AUD': 2}
# Explicit fixture time zones; arbitrary destinations require a user-supplied zone.
DESTINATIONS = {'lisbon, portugal': 'Europe/Lisbon', 'kyoto, japan': 'Asia/Tokyo',
                'chicago, usa': 'America/Chicago', 'paris, france': 'Europe/Paris',
                'jaipur, india': 'Asia/Kolkata'}

def validate_zone(value):
    # Date-only demo schedules use local wall times, never UTC conversions.
    # Restrict to the fixture's known IANA identifiers on Windows without tzdata.
    if value not in set(DESTINATIONS.values()):
        raise ValueError('Choose a supported demo time zone.')

class Problem(Exception):
    def __init__(self, message, status=422, fields=None, code='VALIDATION_ERROR'):
        super().__init__(message)
        self.status, self.fields, self.code = status, fields or {}, code

def now():
    return datetime.now(timezone.utc).isoformat()

def dates(start, end):
    a, b = date.fromisoformat(start), date.fromisoformat(end)
    return [(a + timedelta(days=i)).isoformat() for i in range((b-a).days+1)]

def validate_details(raw):
    d = {k: raw.get(k) for k in ['destination','timeZone','startDate','endDate','travelers',
         'budgetMinor','currency','interests','pace','transport','accessibility','dietary','budgetIncludes']}
    errors = {}
    for k in ['destination','timeZone','startDate','endDate','currency','pace','transport']:
        if not isinstance(d[k], str) or not d[k].strip() or len(d[k]) > 200:
            errors[k] = 'Please provide this detail (up to 200 characters).'
        else:
            d[k] = d[k].strip()
    if isinstance(d['destination'], str) and ',' not in d['destination']:
        errors['destination'] = 'Add a region or country, for example Springfield, Illinois, USA.'
    for k in ['startDate','endDate']:
        try:
            if date.fromisoformat(d[k]).isoformat() != d[k]:
                raise ValueError()
        except (ValueError, TypeError):
            errors[k] = 'Enter a real date as YYYY-MM-DD.'
    if not any(k in errors for k in ['startDate','endDate']):
        count = (date.fromisoformat(d['endDate']) - date.fromisoformat(d['startDate'])).days + 1
        if not 1 <= count <= 14:
            errors['endDate'] = 'Choose an end date on or after the start, for a trip of 1–14 days.'
    if type(d['travelers']) is not int or not 1 <= d['travelers'] <= 12:
        errors['travelers'] = 'Choose 1–12 travelers.'
    if type(d['budgetMinor']) is not int or not 1 <= d['budgetMinor'] <= 10**12:
        errors['budgetMinor'] = 'Enter a positive total party budget.'
    if d['currency'] not in CURRENCIES:
        errors['currency'] = 'Choose a supported currency.'
    if d['pace'] not in ['relaxed','balanced','busy']:
        errors['pace'] = 'Choose relaxed, balanced, or busy.'
    if d['transport'] not in ['walking','public transit','taxi']:
        errors['transport'] = 'Choose a transport option.'
    if d['budgetIncludes'] is None or not isinstance(d['budgetIncludes'], list) or any(x not in ['activities','meals','local transport','accommodation','travel to destination'] for x in d['budgetIncludes']):
        errors['budgetIncludes'] = 'Review budget inclusions.'
    else:
        d['budgetIncludes'] = list(dict.fromkeys(['activities','meals','local transport'] + d['budgetIncludes']))
    if not isinstance(d['interests'], list) or not 1 <= len(d['interests']) <= 8 or any(not isinstance(x, str) or not 1 <= len(x) <= 80 for x in d['interests']):
        errors['interests'] = 'Choose 1–8 interests.'
    for k in ['accessibility','dietary']:
        d[k] = d[k] or ''
        if not isinstance(d[k], str) or len(d[k]) > 500:
            errors[k] = 'Keep this preference under 500 characters.'
    if 'timeZone' not in errors:
        try:
            validate_zone(d['timeZone'])
        except (KeyError, ValueError):
            errors['timeZone'] = 'Choose one of the five supported demo time zones.'
    if errors:
        raise Problem('Please check the highlighted trip details.', fields=errors)
    return d

def recalculate(plan):
    unknown = 0
    for day in plan['days']:
        day['knownTotalMinor'] = sum(x['cost']['amountMinor'] or 0 for x in day['items'])
        unknown += sum(x['cost']['status'] == 'unknown' for x in day['items'])
    total = sum(d['knownTotalMinor'] for d in plan['days'])
    plan['costSummary']['knownTotalMinor'] = total
    plan['costSummary']['unknownCostCount'] = unknown
    plan['costSummary']['budgetStatus'] = 'over' if total > plan['budgetMinor'] else 'uncertain' if unknown else 'within'
    plan['warnings'] = [x for x in plan['warnings'] if not x.startswith('Budget:')]
    if total > plan['budgetMinor']:
        plan['warnings'].append('Budget: known estimates exceed your budget. Try “make day 1 cheaper”, reduce included costs, or increase the budget.')
    if unknown:
        plan['warnings'].append('Budget: some included costs are unknown; the final total may be higher.')
    return plan

def validate_plan(p):
    validate_schema(p)
    if p['currency'] not in CURRENCIES:
        raise ValueError('Unsupported currency')
    validate_zone(p['timeZone'])
    if [d['date'] for d in p['days']] != dates(p['startDate'], p['endDate']):
        raise ValueError('Day coverage does not match trip dates')
    sources = [s['id'] for s in p['sources']]
    if len(sources) != len(set(sources)):
        raise ValueError('Duplicate source IDs')
    seen = set()
    for day in p['days']:
        windows = []
        for item in day['items']:
            if item['id'] in seen or set(item['sourceIds']) - set(sources):
                raise ValueError('Invalid item or source ID')
            seen.add(item['id'])
            c = item['cost']
            if (c['status'] == 'unknown') != (c['amountMinor'] is None) or (c['status'] == 'free' and c['amountMinor'] != 0):
                raise ValueError('Invalid cost status')
            a, b = item['startTime'], item['endTime']
            if (a is None) != (b is None) or (a is not None and b <= a):
                raise ValueError('Invalid time range')
            if a is not None:
                windows.append((a,b))
        windows.sort()
        if any(a[1] > b[0] for a,b in zip(windows, windows[1:])):
            raise ValueError('Overlapping activities')
    correct = recalculate(copy.deepcopy(p))
    if p['costSummary'] != correct['costSummary'] or any(a['knownTotalMinor'] != b['knownTotalMinor'] for a,b in zip(p['days'],correct['days'])):
        raise ValueError('Inconsistent costs')
    return p

class DemoProvider:
    """Only explicit fictional fixtures. Does not make provider calls."""
    def generate(self, trip_id, d):
        timestamp = now()
        p = {'schemaVersion':'1.0','tripId':trip_id,'revision':1,'mode':'demo',
             **{k:d[k] for k in ['destination','timeZone','startDate','endDate','travelers','currency','budgetMinor','budgetIncludes']},
             'assumptions':['All named places are fictional demo fixtures, not real recommendations.',
                            'All prices are illustrative party estimates in your selected currency; no currency conversion is used.',
                            'Transport buffers are rough estimates without route evidence. Opening hours and availability are unverified.',
                            'Full days are assumed; arrival and departure limits have not been supplied.'],
             'warnings':['Verify real prices, opening hours, weather, routes, and availability before travel.'],
             'days':[], 'costSummary':{'knownTotalMinor':0,'unknownCostCount':0,'budgetStatus':'within',
             'exclusions':[x for x in ['accommodation','travel to destination'] if x not in d['budgetIncludes']]},
             'sources':[{'id':'demo-fixtures-v1','provider':'SmartTrip fictional demo fixtures v1','url':None,'retrievedAt':timestamp,'dataStatus':'sample'}],
             'generatedAt':timestamp}
        if d['accessibility']:
            p['warnings'].append('Accessibility request: '+d['accessibility']+'. Step-free access, facilities, and route suitability are unverified; contact real venues.')
        if d['dietary']:
            p['warnings'].append('Dietary request: '+d['dietary']+'. Meal suggestions reflect this preference, but ingredients and suitability need provider verification.')
        # Nominal units deliberately do not imply a real exchange rate or market price.
        unit = 10 ** CURRENCIES[d['currency']]
        for i, day_date in enumerate(dates(d['startDate'],d['endDate'])):
            day = {'date':day_date,'title':['A gentle introduction','Culture & little discoveries','A different side of the city'][i%3],'items':[],'knownTotalMinor':0}
            def add(kind,title,a,b,price,notes=''):
                day['items'].append({'id':f'd{i+1}-{len(day["items"])+1}','kind':kind,'title':title,
                    'startTime':a,'endTime':b,'location': 'Fictional demo district' if kind not in ['rest','lodging','other'] else None,
                    'notes':notes,'cost':{'amountMinor':None if price is None else price*unit*d['travelers'],
                    'status':'unknown' if price is None else 'free' if price == 0 else 'estimate'},
                    'sourceIds':['demo-fixtures-v1'],'verification':'sample'})
            interest = d['interests'][i % len(d['interests'])].lower()
            venue = 'Sample Mosaic Museum' if any(x in interest for x in ['culture','museum','art','history']) else 'Sample Willow Gardens' if any(x in interest for x in ['nature','outdoor']) else 'Sample Makers Market'
            add('meal','Sample Corner Café · breakfast','09:00','09:45',10,d['dietary'] or 'Illustrative breakfast stop.')
            add('transport','Local travel buffer','09:45','10:15',4 if d['transport'] != 'walking' else 0,'Rough 30-minute buffer; route and distance unverified.')
            add('activity',venue,'10:15','11:45',24,'Fictional '+interest+' suggestion. Opening hours are not verified.')
            add('meal','Sample Courtyard Kitchen · lunch','12:15','13:15',18,d['dietary'] or 'Allow time for a relaxed lunch.')
            add('rest','Pause & recharge','13:15','14:15' if d['pace']=='relaxed' else '13:45',0,'Find a comfortable place to rest; facilities unverified.')
            add('transport','Afternoon travel buffer','14:15','14:45',4 if d['transport'] != 'walking' else 0,'Rough estimate, not a verified route.')
            add('activity','Sample Riverside Walk' if d['pace']=='relaxed' else 'Sample Studio Gallery','14:45','16:00',0 if d['pace']=='relaxed' else 16,'Fictional stop; verify terrain and access with real providers.')
            if d['pace']=='busy':
                add('activity','Sample Lantern Workshop','16:30','17:30',28,'Fictional optional workshop.')
            add('meal','Sample Evening Table · dinner','18:00','19:00',24,d['dietary'] or 'Illustrative dinner stop.')
            if 'accommodation' in d['budgetIncludes']:
                add('lodging','Accommodation estimate',None,None,70,'Illustrative per-person nightly allocation, including the last day; adjust to your actual stay.')
            if i == 0 and 'travel to destination' in d['budgetIncludes']:
                add('other','Travel to destination',None,None,None,'Enter a real party quote when known; not included in the known total.')
            p['days'].append(day)
        return validate_plan(recalculate(p))

def revise(plan, payload):
    p = copy.deepcopy(plan)
    request = payload.get('request','')
    if not isinstance(request,str) or len(request)>2000:
        raise Problem('Keep revision requests under 2,000 characters.')
    day_number = payload.get('day')
    if day_number is None:
        match = re.search(r'day\s+(\d+|one|two|three|four)',request.lower())
        words = {'one':1,'two':2,'three':3,'four':4}
        day_number = words.get(match[1],int(match[1]) if match and match[1].isdigit() else 1) if match else 1
    if type(day_number) is not int or not 1 <= day_number <= len(p['days']):
        raise Problem('Choose a day in your itinerary.')
    day = p['days'][day_number-1]
    action = payload.get('action')
    if not action:
        text = request.lower()
        action = 'cheaper' if any(x in text for x in ['cheap','budget','less expensive']) else 'break' if any(x in text for x in ['break','rest','relax']) else 'replace' if any(x in text for x in ['replace','museum','swap']) else None
    activities = [x for x in day['items'] if x['kind']=='activity']
    target = next((x for x in activities if x['id']==payload.get('itemId')), None)
    if payload.get('itemId') and target is None and action not in ['cost','edit']:
        raise Problem('That activity no longer exists. Refresh the plan.',409,code='REVISION_CONFLICT')
    target = target or (activities[0] if activities else None)
    if action=='cheaper':
        for x in activities:
            x.update(title='Sample Neighborhood Discovery',notes='Fictional free alternative. Verify a real route and access before travel.')
            x['cost']={'amountMinor':0,'status':'free'}
        change = f'Day {day_number}: replaced paid activities with fictional free alternatives.'
    elif action=='replace' and target:
        target.update(title='Sample Botanical Courtyard',notes='Fictional alternative. Access and opening hours unverified.')
        target['cost']={'amountMinor':0,'status':'free'}
        change = f'Day {day_number}: replaced one activity; other items were preserved.'
    elif action=='break' and target:
        target.update(kind='rest', title='Extra time to rest',location=None,notes='An activity slot has become a break; the schedule stays clear.')
        target['cost']={'amountMinor':0,'status':'free'}
        change = f'Day {day_number}: changed one activity slot into a break.'
    elif action=='edit':
        title = payload.get('title')
        if not isinstance(title,str) or not 1<=len(title.strip())<=120:
            raise Problem('Enter a day title of 1–120 characters.')
        day['title']=title.strip()
        change=f'Day {day_number}: updated the day title.'
    elif action=='cost':
        item=next((x for x in day['items'] if x['id']==payload.get('itemId')),None)
        amount=payload.get('amountMinor')
        if item is None or (amount is not None and (type(amount) is not int or not 0<=amount<=10**12)):
            raise Problem('Enter a valid whole-party cost or mark it unknown.')
        item['cost']={'amountMinor':amount,'status':'unknown' if amount is None else 'free' if amount==0 else 'estimate'}
        change=f'Day {day_number}: updated one party cost.'
    else:
        raise Problem('Try “make day two cheaper”, “replace an activity on day 1”, or “add a break on day 3”.',400,code='UNSUPPORTED_REQUEST')
    p['revision']+=1
    p['generatedAt']=now()
    return validate_plan(recalculate(p)), change

def chat_reply(message):
    text=message.lower()
    if any(x in text for x in ['visa','medical','safe','emergency','passport','api key','ignore instructions']):
        return 'I can help with general planning. Entry rules, health, safety, and accessibility need current official verification; I cannot guarantee them. In an immediate emergency, contact local emergency services or nearby staff. Do not share passwords, payment details, or travel documents.'
    if any(x in text for x in ['book','buy','pay','reserve']):
        return 'I can plan your trip, but cannot book or pay. Check prices and availability directly with a real provider.'
    if 'springfield' in text:
        return 'Which Springfield do you mean? Please add its region and country, then choose exact start and end dates in Trip details.'
    return 'Use Trip details to confirm the destination, exact dates, party budget, and preferences. In this demo, chat can revise a generated plan: try “make day two cheaper”, “replace an activity on day 1”, or “add a break on day 2”.'

def extract_intake(message):
    """Bounded rule-based demo intake; never guess ambiguous dates or places."""
    text=message.lower()
    fields={}
    if any(x in text for x in ['visa','medical','safe','emergency','passport','api key','ignore instructions','book','buy','pay','reserve']):
        return {'fields':{},'reply':chat_reply(message)}
    for destination,zone in DESTINATIONS.items():
        if destination.split(',')[0] in text:
            fields['destination']=destination.title().replace('Usa','USA')
            fields['timeZone']=zone
            break
    found=re.findall(r'\b\d{4}-\d{2}-\d{2}\b',message)
    if len(found)>=2: fields.update(startDate=found[0],endDate=found[1])
    travelers=re.search(r'\b(\d+)\s*(?:people|travelers|travellers|adults|persons)',text)
    if travelers: fields['travelers']=int(travelers[1])
    elif re.search(r'\b(?:for two|two people|two travelers)\b',text): fields['travelers']=2
    budget=re.search(r'\b(USD|EUR|GBP|INR|JPY|CAD|AUD)\s*([\d,]+(?:\.\d+)?)',message,re.I)
    if not budget:
        budget=re.search(r'([\d,]+(?:\.\d+)?)\s*(USD|EUR|GBP|INR|JPY|CAD|AUD)\b',message,re.I)
        if budget: fields.update(currency=budget[2].upper(),budget=budget[1].replace(',',''))
    else: fields.update(currency=budget[1].upper(),budget=budget[2].replace(',',''))
    interests=[x for x in ['food','culture','nature','museums','art','history','outdoors'] if x in text]
    if interests: fields['interests']=interests
    if any(x in text for x in ['relax','slow','break']):fields['pace']='relaxed'
    if 'busy' in text:fields['pace']='busy'
    if 'vegetarian' in text:fields['dietary']='Vegetarian meals'
    if 'step-free' in text:fields['accessibility']='Step-free access requested'
    questions=[]
    if 'destination' not in fields:questions.append('Which city, region, and country do you mean?')
    if 'startDate' not in fields:questions.append('What exact start and end dates? Use YYYY-MM-DD, or fill in the dates below.')
    reply='I’ve added the details I could read to the form. Please review them; no itinerary is generated until you confirm.' if fields else 'Let’s make your trip more specific.'
    return {'fields':fields,'reply':reply+' '+(' '.join(questions[:2]) if questions else 'How many people are going, and what is the total party budget? Review those fields below.')}

def markdown(p):
    def clean(s):
        return str(s).replace('\n',' ').replace('<','&lt;').replace('>','&gt;')
    def money(n):
        return 'Unknown' if n is None else f'{p["currency"]} {n / 10**CURRENCIES[p["currency"]]:.{CURRENCIES[p["currency"]]}f}'
    lines=[f'# {clean(p["destination"])}',f'DEMO · fictional places · revision {p["revision"]}',f'{p["startDate"]} → {p["endDate"]} · {p["travelers"]} travelers · {p["timeZone"]}',f'Budget: {money(p["budgetMinor"])} (entire party)',f'Includes: {", ".join(p["budgetIncludes"])}','']
    for d in p['days']:
        lines += [f'## {d["date"]} · {clean(d["title"])}']
        for x in d['items']:
            lines += [f'- {x["startTime"] or "Unscheduled"}–{x["endTime"] or ""} {clean(x["title"])} · {money(x["cost"]["amountMinor"])} ({x["cost"]["status"]}, {x["verification"]})',f'  {clean(x["location"] or "")} {clean(x["notes"])} · sources: {", ".join(x["sourceIds"])}']
        lines += [f'Day known total: {money(d["knownTotalMinor"])}','']
    lines += [f'Known trip total: {money(p["costSummary"]["knownTotalMinor"])}',f'Budget status: {p["costSummary"]["budgetStatus"]}',f'Unknown costs: {p["costSummary"]["unknownCostCount"]}',f'Exclusions: {", ".join(p["costSummary"]["exclusions"]) or "None"}','## Assumptions & warnings']
    lines += ['- '+clean(x) for x in p['assumptions']+p['warnings']]
    lines += ['## Sources']+['- '+clean(s['provider'])+' · '+s['dataStatus']+' · '+s['retrievedAt'] for s in p['sources']]
    return '\n'.join(lines)+'\n'
