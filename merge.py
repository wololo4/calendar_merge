import requests
from icalendar import Calendar

out=Calendar()
seen=set()
with open("feeds.txt") as f:
    urls=[l.strip() for l in f if l.strip() and not l.startswith("#")]
for url in urls:
    data=requests.get(url,timeout=30).content
    cal=Calendar.from_ical(data)
    for c in cal.walk():
        if c.name!="VEVENT": continue
        uid=str(c.get("UID",""))+str(c.get("DTSTART",""))
        if uid in seen: continue
        seen.add(uid)
        out.add_component(c)
with open("calendar.ics","wb") as f:
    f.write(out.to_ical())
print("Created calendar.ics")
