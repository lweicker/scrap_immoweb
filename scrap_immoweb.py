from typing import Optional, List
import os
import traceback
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import json

from dotenv import load_dotenv
import requests
import pandas as pd
from pydantic import BaseModel


load_dotenv(dotenv_path=".env")

SENDER_EMAIL = os.getenv("SENDER_EMAIL")
MAIL_PASSWORD = os.getenv("SENDER_PASSWORD")
RECIPIENTS = json.loads(os.getenv("RECIPIENTS"))
POSTCODES = "6700"
MAX_PRICE = "600000"  # €
MIN_LAND_SURFACE = "700"  # m²
URL_TEMPLATE = "https://www.immoweb.be/fr/search-results/terrain-a-batir/a-vendre?countries=BE" \
               "&maxPrice={max_price}&minLandSurface={min_land_surface}&postalCodes=BE-{postcodes}" \
               "&priceType=PRICE&page={page}&orderBy=relevance"

OLD_RESULT_PATH = "last_result.json"
current_page = 1


class LocationModel(BaseModel):
    country: Optional[str] = None
    region: Optional[str] = None
    province: Optional[str] = None
    district: Optional[str] = None
    locality: Optional[str] = None
    postalCode: Optional[str] = None
    regionCode: Optional[str] = None


class PropertyModel(BaseModel):
    type: Optional[str] = None
    subtype: Optional[str] = None
    title: Optional[str] = None
    location: LocationModel
    netHabitableSurface: Optional[float] = None
    landSurface: Optional[float] = None


class SaleModel(BaseModel):
    price: Optional[float] = None
    pricePerSqm: Optional[float] = None
    toBuild: Optional[str] = None


class TransactionModel(BaseModel):
    type: Optional[str] = None
    sale: SaleModel


class ResultSearchModel(BaseModel):
    id: int
    property: PropertyModel
    transaction: TransactionModel


class ResponseSearchImmowebModel(BaseModel):
    results: List[ResultSearchModel]


def _extract_new_results(old_list_results: List[ResultSearchModel], current_list_results: List[ResultSearchModel]) \
        -> List[ResultSearchModel]:
    old_ids = [i.id for i in old_list_results]
    difference_results: List[ResultSearchModel] = []

    for current_result in current_list_results:
        if current_result.id not in old_ids:
            difference_results.append(current_result)

    return difference_results


def _save_results(list_results: List[ResultSearchModel]) -> None:
    results_as_json = [result.model_dump() for result in list_results]
    with open(OLD_RESULT_PATH, "w") as output_file:
        output_file.write(json.dumps(results_as_json, indent=4))


def _get_old_results() -> List[ResultSearchModel]:
    if os.path.isfile(OLD_RESULT_PATH):
        with open(OLD_RESULT_PATH, 'r') as my_file:
            raw_data = my_file.read()
        previous_results = json.loads(raw_data)
        return [ResultSearchModel(**element) for element in previous_results]
    return []


def _convert_model_to_dataframe(list_results: List[ResultSearchModel]) -> pd.DataFrame:
    filtered_results = []
    for element in list_results:
        filtered_results.append([f"https://www.immoweb.be/fr/annonce/{element.id}", element.property.location.locality,
                                 element.property.landSurface, element.transaction.sale.price,
                                 element.transaction.sale.pricePerSqm])
    df = pd.DataFrame(filtered_results, columns=['Lien', 'Ville', 'Superficie', 'Prix', 'Prix/m²'])
    return df


def _send_mail(list_results: List[ResultSearchModel]) -> None:
    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = ', '.join(RECIPIENTS)
        msg['Subject'] = f" {len(list_results)} nouveaux terrains à bâtir"
        data_frame = _convert_model_to_dataframe(list_results)
        html = """\
                <html>
                <head></head>
                <body>
                    {0}
                </body>
                </html>
                """.format(data_frame.to_html())
        part_1 = MIMEText(html, 'html')
        msg.attach(part_1)

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp_server:
            smtp_server.login(SENDER_EMAIL, MAIL_PASSWORD)
            smtp_server.sendmail(SENDER_EMAIL, RECIPIENTS, msg.as_string())
    except:
        traceback.print_exc()


results: List[ResultSearchModel] = []

while True:
    url = URL_TEMPLATE.format(max_price=MAX_PRICE, min_land_surface=MIN_LAND_SURFACE, postcodes=POSTCODES,
                              page=current_page)
    response = requests.request("GET", url)
    response_as_json_object = json.loads(response.text)
    formatted_response = ResponseSearchImmowebModel(**response_as_json_object)
    results_for_current_page = formatted_response.results
    if not results_for_current_page or response.status_code != 200:
        break

    results.extend(results_for_current_page)
    current_page += 1

results.sort(key=lambda x: x.id, reverse=False)
old_results = _get_old_results()
new_results = _extract_new_results(old_results, results)
print(f'new_results since last run: {new_results}')
print(f'Number new results since last run: {len(new_results)}')

_save_results(results)
if new_results:
    _send_mail(new_results)
