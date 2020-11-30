from ratelimit import limits, sleep_and_retry
import requests
import json

osm = "https://www.openstreetmap.org/api/0.6/relation/{id}"
nominatim = "https://nominatim.openstreetmap.org/lookup"
istanbul_id = "223474"

ilce_geojson = {
    "type": "FeatureCollection",
    "name": "İstanbul İlçeleri",
    "licence": "Data © OpenStreetMap contributors, ODbL 1.0. https://osm.org/copyright",
    "features": []
}

mahalle_geojson = {
    "type": "FeatureCollection",
    "name": "İstanbul Mahalleleri",
    "licence": "Data © OpenStreetMap contributors, ODbL 1.0. https://osm.org/copyright",
    "features": []
}


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


@sleep_and_retry
@limits(calls=1, period=1)
def get_full(rel_id):
    r = requests.get(osm.format(id=rel_id), headers={"Accept": "application/json"})
    if r.status_code == 200:
        data = json.loads(r.content)
        return data


def get_subareas(elements):
    return [member["ref"] for member in elements["members"] if member["role"] == "subarea"]


@sleep_and_retry
@limits(calls=1, period=1)
def get_geojson(rel_ids):
    r = requests.get(nominatim, params={
        "osm_ids": ",".join(["R" + str(id_) for id_ in rel_ids]),
        "format": "geojson",
        "polygon_geojson": 1
    })

    if r.status_code != 200:
        raise Exception('API response: {}'.format(r.status_code))
    return json.loads(r.content)


def write_to_file(filename, obj):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def main():
    istanbul_full = get_full(istanbul_id)
    subareas = get_subareas(istanbul_full["elements"][0])

    ilce_geojson["features"].extend(get_geojson(subareas)["features"])
    write_to_file("ilce_geojson.json", ilce_geojson)

    mahalleler = [mahalle for s in subareas for mahalle in get_subareas(get_full(s)["elements"][0])]
    for chunk in chunks(mahalleler, 50):
        mahalle_geojson["features"].extend(get_geojson(chunk)["features"])

    write_to_file("mahalle_geojson.json", mahalle_geojson)


if __name__ == "__main__":
    main()
