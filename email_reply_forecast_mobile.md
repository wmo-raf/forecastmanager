Subject: Re: ClimWeb mobile forecast endpoint + locations

Hi,

Thanks — glad it looks good. Let me tighten up a couple of points, because there's one distinction that actually works in our favour for the fallback idea.

**On the `forecast_mobile` endpoint**

It's slightly different from "a bridge to another forecasting system." The endpoint serves ClimWeb's *own* stored forecasts — whatever the NMHS has in ClimWeb, whether that was entered manually by a forecaster or auto-generated from yr.no or Open-Meteo. Those three are the *sources ClimWeb ingests*, not separate systems the endpoint reaches out to at request time.

What the endpoint does do is return that forecast in the **same shape as the yr.no / api.met.no `locationforecast` model** — a `timeseries` array where each step carries `time`, `data.instant.details` (the values), and `data.next_1_hours.summary.symbol_code` (the weather condition). We deliberately trimmed it to just those fields for mobile.

**Why that helps your fallback plan**

Because the response mirrors the yr.no structure, the app doesn't really need to support "several APIs" with separate parsers. It can use **one parser** and just switch the base URL: ClimWeb first, and if ClimWeb is unreachable, fall straight through to api.met.no (or another locationforecast-compatible source). Same JSON shape, same parsing code. So you're right that it's trivial — and it's trivial precisely because the formats line up rather than because there's a second integration to build.

**On locations / place names**

This is the part worth aligning on. A couple of things about how ClimWeb handles it:

ClimWeb stores forecasts per **city**, and `forecast_mobile` is queried by **coordinates** (`?lat=&lon=`), not by name — it matches the request to the **nearest stored city** and returns that. So the app never has to match place-name strings against ClimWeb; it sends lat/lon and gets back the nearest city's forecast (the response also tells you whether it was an exact or nearest match). That sidesteps most of the place-name-handling pain.

The open question is scale. ClimWeb isn't designed to hold tens of thousands of locations per country the way your shipped data dump does — and I'd argue it shouldn't need to. For an NMHS forecast product, the meaningful unit is administrative/population centres, not every hamlet. To support that cleanly we've **added a GeoNames import to ClimWeb**: an admin picks a country and ClimWeb pulls cities from GeoNames, filtered to populated places and capped at a manageable number (default 200) by taking all administrative seats (national/regional/district capitals) plus the highest-population towns.

That points to what I think is the right shared answer to your last question. Rather than each side maintaining its own location list, we use **GeoNames as the common backbone for both** — the app and ClimWeb reference the same canonical places (and GeoNames IDs as stable identifiers). Then:

- If the app should keep serving its full fine-grained list, it can continue to do so locally, but the nearest-city matching on the ClimWeb side means it still gets a forecast for any coordinate without ClimWeb needing every point.
- If we want true parity, we decide together on a sensible per-country set drawn from GeoNames, shared by both, instead of a static dump baked into the app.

So my suggestion: keep the data dump out of the long-term picture, standardise on GeoNames, and let the app query ClimWeb by coordinates with an api.met.no fallback. Happy to jump on a call to nail down the location set and the exact fallback behaviour.

Best,
Grace
