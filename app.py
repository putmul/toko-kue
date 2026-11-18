import os

from flask import Flask

from routes.auth import register as register_auth
from routes.customer import register as register_customer
from routes.customer_expert import register as register_customer_expert
from routes.admin import register as register_admin
from routes.office import register as register_office
from routes.cashier import register as register_cashier
from routes.logout import register as register_logout
from routes.knowledge import register as register_knowledge
from routes.mis import register as register_mis
from routes.dss import register as register_dss 
from routes.expert import register as register_expert


app = Flask(__name__)
app.secret_key = os.environ.get(
    "SISTEM_TRANSAKSI_SECRET_KEY",
    "change-this-secret-key-before-production"
)

register_auth(app)
register_customer(app)
register_customer_expert(app)
register_admin(app)
register_office(app)
register_cashier(app)
register_logout(app)
register_knowledge(app)
register_mis(app)
register_dss(app)
register_expert(app)


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "0") == "1")
