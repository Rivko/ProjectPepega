def extract_id_from_url(url: str) -> str:
    """Returns sheet_id from google spreadsheet url"""
    sheet_id = url.split("spreadsheets/d/")[1]
    if "/" in sheet_id:
        sheet_id = sheet_id.split("/")[0]
    return sheet_id


def get_full_url(sheet_id: str, sheet_name: str) -> str:
    """Returns combined csv url from sheet_id and sheet_name"""
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
