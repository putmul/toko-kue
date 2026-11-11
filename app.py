from flask import Flask

from routes.auth import register as register_auth
from routes.customer import register as register_customer
from routes.admin import register as register_admin
from routes.office import register as register_office
from routes.cashier import register as register_cashier
from routes.logout import register as register_logout
from routes.knowledge import register as register_knowledge
from routes.mis import register as register_mis
from routes.dss import register as register_dss 
from routes.expert import register as register_expert


app = Flask(__name__)
app.secret_key = "sistem-transaksi-secret-key"

register_auth(app)
register_customer(app)
register_admin(app)
register_office(app)
register_cashier(app)
register_logout(app)
register_knowledge(app)
register_mis(app)
register_dss(app)
register_expert(app)


if __name__ == "__main__":
    app.run(debug=True)
