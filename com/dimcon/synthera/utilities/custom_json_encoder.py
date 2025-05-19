import json
from datetime import datetime, date
from decimal import Decimal

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()  # convert to ISO format string
        if isinstance(obj, Decimal):
            return float(obj)  # safely convert Decimal to float
        return super().default(obj)
