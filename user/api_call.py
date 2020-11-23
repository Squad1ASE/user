import requests
import json

def RESERVATION_contact_tracing(customer_email):
    data = dict(email=customer_email)

    return requests.post('http://127.0.0.1:5000/stub/reservations')