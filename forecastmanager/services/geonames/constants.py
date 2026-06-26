"""
GeoNames feature codes and request constants.

Reference: https://www.geonames.org/export/codes.html

Only feature class ``P`` (populated places) is relevant for cities. Within that
class, the ``PPL*`` codes describe how administratively important a place is.
"""

#: GeoNames search web service (JSON).
GEONAMES_SEARCH_URL = "http://api.geonames.org/searchJSON"

#: Feature class for populated places (cities, towns, villages).
FEATURE_CLASS_POPULATED = "P"

#: National capital.
PPLC = "PPLC"
#: Seat of a first-order administrative division (regional/provincial capital).
PPLA = "PPLA"
#: Seats of second- to fifth-order administrative divisions (district/ward seats).
PPLA2 = "PPLA2"
PPLA3 = "PPLA3"
PPLA4 = "PPLA4"
PPLA5 = "PPLA5"
#: Generic populated place (the bulk: towns, villages, hamlets).
PPL = "PPL"

#: Administrative-seat codes we always try to include, in priority order.
#: A lower index means higher priority when the cap forces a trade-off.
ADMIN_SEAT_CODES = [PPLC, PPLA, PPLA2]

#: Rank used to order places of equal importance is population; this maps a
#: feature code to a primary sort key (smaller sorts first / more important).
FEATURE_CODE_PRIORITY = {
    PPLC: 0,
    PPLA: 1,
    PPLA2: 2,
    PPLA3: 3,
    PPLA4: 4,
    PPLA5: 5,
    PPL: 6,
}

#: GeoNames caps maxRows at 1000 per request.
GEONAMES_MAX_ROWS = 1000

#: Default ceiling on the number of cities imported in one run.
DEFAULT_MAX_CITIES = 200
