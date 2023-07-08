import csv

"""
Required fields when inserting into the database.
"""

_required_fields = [
    # the "str" type means that this field can be any valid string.
    ("metabolite_name",     "str"),
    ("formula",             "str"),
    # any field labeled a "float" needs to have a value in decimal notation.
    ("monoisotopic_mass",                "float"),
    ("mode",                "str"),

    ("final_mz",            "float"),
    ("final_rt",            "float"),
    ("final_adduct",        "str"),
    ("standard_grp",        "str"),
    ("msms_detected",       "yesno"),  # Value can either be "Yes" or "No"
    ("inchikey",            "str"),
]


"""
Optional fields and corresponding types when batch inserting into the database.
"""

_optional_fields = [
    ("chemical_db_id",      "str"),
    ("library",             "str"),

    ("pubchem_cid",         "int"),  # Only integers are permitted.
    ("pubmed_refcount",     "int"),
    ("inchikey14",          "str"),

    ("detected_adducts",    "str"),
    ("adduct_calc_mz",      "str"),
    ("msms_purity",         "float"),
]

"""
All fields (excluding those that are commented) are mandatory to include.
"""

_query_fields = [
    ("rt_min",                "float"),
    ("rt_max",                "float"),

    ("mz_min",                "float"),
    ("mz_max",                "float"),

    ("mode",                "str"),

    #    ("year_max",                "int"),
    #    ("day_max",                 "int"),
    #    ("month_max",               "int"),
]


def _validate_type(field: str, value: str, t):
    if t == "yesno":
        l = value.strip().lower()
        if l == "yes":
            return True
        elif l == "no":
            return False
        else:
            raise ValueError(
                f"Yes/No field {field} does not have a valid value {value}")
    elif t == "int":
        try:
            return int(value)
        except ValueError:
            raise ValueError(
                f"Integer field {field} does not have a valid value {value}")
    elif t == "float":
        try:
            return float(value)
        except ValueError:
            raise ValueError(
                f"Float field {field} does not have a valid value {value}")
    elif t == "str":
        return value
    else:
        raise ValueError(f"Impossible field type {t}")


def validate_insertion_csv_fields(reader: csv.DictReader) -> tuple[list[dict], str]:
    chemicals: list[dict] = []
    for row in reader:
        chemical = {}
        for field, t in _required_fields:
            if field not in row:
                return [], f"Required field \"{field}\" not present in csv"
            try:
                value = _validate_type(field, row[field], t)
                chemical[field] = value
            except ValueError as e:
                return [], str(e)

        for field, t in _optional_fields:
            if field not in row:
                continue
            try:
                value = _validate_type(field, row[field], t)
                chemical[field] = value
            except ValueError as e:
                return [], str(e)
        chemicals.append(chemical)
    return chemicals, ""


def validate_query_csv_fields(reader: csv.DictReader) -> tuple[list[dict], str]:
    queries: list[dict] = []
    for row in reader:
        query = {}
        for field, t in _query_fields:
            if field not in row:
                return [], f"Required field \"{field}\" not present in csv"
            try:
                value = _validate_type(field, row[field], t)
                query[field] = value
            except ValueError as e:
                return [], str(e)

        # year_max, month_max, day_max = query.get(
        #    'year_max'), query.get('month_max'), query.get('day_max')
        # try:
        #    d = date(year_max, month_max, day_max)
        #    query["date"] = d
        # except ValueError as e:
        #    return [], f"Invalid Date Value Provided for {month_max}/{day_max}/{year_max}"
        queries.append(query)
    return queries, ""
