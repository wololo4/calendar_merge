from icalendar import Event

class ICSEventBuilder:
    def __init__(self):
        self.event = Event()
    def uid(self, uid):
        self.event.add("uid", uid)
        return self
    def start(self, start_dt):
        self.event.add("dtstart", start_dt)
        return self
    def end(self, end_dt):
        self.event.add("dtend", end_dt)
        return self
    def summary(self, summary):
        self.event.add("summary", summary)
        return self
    def location(self, venue):
        self.event.add("location", venue)
        return self
    def description(self, description):
        if description:
            self.event.add("description", description)
        else:
            self.event.add("description", "")
        return self
    def build(self):
        return self.event