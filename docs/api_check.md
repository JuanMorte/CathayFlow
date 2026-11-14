# API check

Written by `make check-apis` on 2026-11-14 19:04 HKT. Structure and field names only: no keys, account IDs or raw OAG records.

## AWS: PASS

- Identity: `arn:aws:sts::************:assumed-role/<id>/Hackathon-Team06`, region `ap-southeast-1`.
- S3: put, get and delete of `healthcheck.txt` in the data bucket work.
- SSM: 5 of 5 keys stored (oag-key-dev, oag-connections-key-dev, oag-key-demo, oag-connections-key-demo, google-routes-key).

## HKIA past flights: PASS

- 2026-11-13 arrivals: 420 flights, 165 operated by CX, stand filled 100%. Status shapes: `At gate 99:99` × 411; `At gate 99:99 (99/99/9999)` × 8; `Cancelled` × 1.
- 2026-11-13 departures: 417 flights, 161 operated by CX, gate filled 100%. Status shapes: `Dep 99:99` × 413; `Dep 99:99 (99/99/9999)` × 3; `Cancelled` × 1.
- Recorder Lambda `flow-hkia-recorder` answered {"stored": 0, "skipped": 2, "empty": 0, "failed": 0} and both files are in S3. HKIA answers AWS Lambda IPs (the backfill fetched 182 files from Lambda).

## OAG Flight Info: PASS

- Top-level keys: `['data', 'paging']`; paging: `{"limit": 10, "totalCount": 329, "totalPages": 33, "next": true}` (`next` is a full URL with an `After=` cursor when true).
- 10 records on the first page; one record has 86 field paths.
- Estimated and actual times: `statusDetails[].arrival.actualTime`, `statusDetails[].arrival.actualTime.onGround`, `statusDetails[].arrival.actualTime.onGround.local`, `statusDetails[].arrival.actualTime.onGround.utc`, `statusDetails[].arrival.estimatedTime`, `statusDetails[].arrival.estimatedTime.onGround`, `statusDetails[].arrival.estimatedTime.onGround.local`, `statusDetails[].arrival.estimatedTime.onGround.utc`, `statusDetails[].departure.actualTime`, `statusDetails[].departure.actualTime.offGround`, `statusDetails[].departure.actualTime.offGround.local`, `statusDetails[].departure.actualTime.offGround.utc`, `statusDetails[].departure.estimatedTime`, `statusDetails[].departure.estimatedTime.offGround`, `statusDetails[].departure.estimatedTime.offGround.local`, `statusDetails[].departure.estimatedTime.offGround.utc`, `statusDetails[].departure.estimatedTime.outGate`, `statusDetails[].departure.estimatedTime.outGate.local`, `statusDetails[].departure.estimatedTime.outGate.utc`, `statusDetails[].departure.estimatedTime.outGateTimeliness`, `statusDetails[].departure.estimatedTime.outGateVariation`.
- Status updates on that flight: 13; sorted by `updatedAt`: False; states seen: `['InAir', 'Landed', 'Scheduled']`.
- History: 2026-10-14 returns 10 records on page one, 8 with status updates.
- SEATS (capacity, not free seats): `seatingCapacity`, `seatingCapacity.predicted`, `seatingCapacity.predicted.businessClass`, `seatingCapacity.predicted.economyClass`, `seatingCapacity.predicted.economyPlusClass`, `seatingCapacity.predicted.firstClass`, `seatingCapacity.predicted.premiumEconomyClass`, `seatingCapacity.predicted.totalSeats`.
- OAG live calls in the last 30 days (this key): 4 of 800.
- All field paths of one record: `aircraftType`, `aircraftType.iata`, `aircraftType.icao`, `arrival`, `arrival.airport`, `arrival.airport.iata`, `arrival.airport.icao`, `arrival.country`, `arrival.country.code`, `arrival.date`, `arrival.date.local`, `arrival.date.utc`, `arrival.time`, `arrival.time.local`, `arrival.time.utc`, `carrier`, `carrier.iata`, `carrier.icao`, `codeshare`, `codeshare.<id>`, `codeshare.marketingFlights`, `departure`, `departure.airport`, `departure.airport.faa`, `departure.airport.iata`, `departure.airport.icao`, `departure.country`, `departure.country.code`, `departure.date`, `departure.date.local`, `departure.date.utc`, `departure.time`, `departure.time.local`, `departure.time.utc`, `distance`, `elapsedTime`, `flightNumber`, `flightType`, `segmentInfo`, `segmentInfo.intermediateAirports`, `segmentInfo.intermediateAirports.iata`, `segmentInfo.numberOfStops`, `serviceType`, `statusDetails`, `statusDetails[].arrival`, `statusDetails[].arrival.actualTime`, `statusDetails[].arrival.actualTime.onGround`, `statusDetails[].arrival.actualTime.onGround.local`, `statusDetails[].arrival.actualTime.onGround.utc`, `statusDetails[].arrival.airport`, `statusDetails[].arrival.airport.iata`, `statusDetails[].arrival.airport.icao`, `statusDetails[].arrival.country`, `statusDetails[].arrival.country.code`, `statusDetails[].arrival.estimatedTime`, `statusDetails[].arrival.estimatedTime.onGround`, `statusDetails[].arrival.estimatedTime.onGround.local`, `statusDetails[].arrival.estimatedTime.onGround.utc`, `statusDetails[].departure`, `statusDetails[].departure.actualTime`, `statusDetails[].departure.actualTime.offGround`, `statusDetails[].departure.actualTime.offGround.local`, `statusDetails[].departure.actualTime.offGround.utc`, `statusDetails[].departure.airport`, `statusDetails[].departure.airport.faa`, `statusDetails[].departure.airport.iata`, `statusDetails[].departure.airport.icao`, `statusDetails[].departure.country`, `statusDetails[].departure.country.code`, `statusDetails[].departure.estimatedTime`, `statusDetails[].departure.estimatedTime.offGround`, `statusDetails[].departure.estimatedTime.offGround.local`, `statusDetails[].departure.estimatedTime.offGround.utc`, `statusDetails[].departure.estimatedTime.outGate`, `statusDetails[].departure.estimatedTime.outGate.local`, `statusDetails[].departure.estimatedTime.outGate.utc`, `statusDetails[].departure.estimatedTime.outGateTimeliness`, `statusDetails[].departure.estimatedTime.outGateVariation`, `statusDetails[].equipment`, `statusDetails[].equipment.actualAircraftType`, `statusDetails[].equipment.actualAircraftType.iata`, `statusDetails[].equipment.actualAircraftType.icao`, `statusDetails[].equipment.aircraftRegistrationNumber`, `statusDetails[].state`, `statusDetails[].updatedAt`, `statusKey`.

## Google Routes: PASS

- Central → HKIA T1, departure in 2 h, PESSIMISTIC: 38 min with traffic, 30 min static.
- Central → HKIA T1, departure in 2 h, BEST_GUESS: 30 min with traffic, 30 min static.
