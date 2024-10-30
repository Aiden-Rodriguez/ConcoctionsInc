from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
from enum import Enum
import sqlalchemy
from src import database as db
from src.api.inventory import get_gold_quan, get_ml_quan, get_potion_quan

router = APIRouter(
    prefix="/carts",
    tags=["cart"],
    dependencies=[Depends(auth.get_api_key)],
)

class search_sort_options(str, Enum):
    customer_name = "customer_name"
    item_sku = "item_sku"
    line_item_total = "line_item_total"
    timestamp = "timestamp"

class search_sort_order(str, Enum):
    asc = "asc"
    desc = "desc"   

@router.get("/search/", tags=["search"])
def search_orders(
    customer_name: str = "",
    potion_sku: str = "",
    search_page: str = "",
    sort_col: search_sort_options = search_sort_options.timestamp,
    sort_order: search_sort_order = search_sort_order.desc,
):
    """
    Search for cart line items by customer name and/or potion sku.

    Customer name and potion sku filter to orders that contain the 
    string (case insensitive). If the filters aren't provided, no
    filtering occurs on the respective search term.

    Search page is a cursor for pagination. The response to this
    search endpoint will return previous or next if there is a
    previous or next page of results available. The token passed
    in that search response can be passed in the next search request
    as search page to get that page of results.

    Sort col is which column to sort by and sort order is the direction
    of the search. They default to searching by timestamp of the order
    in descending order.

    The response itself contains a previous and next page token (if
    such pages exist) and the results as an array of line items. Each
    line item contains the line item id (must be unique), item sku, 
    customer name, line item total (in gold), and timestamp of the order.
    Your results must be paginated, the max results you can return at any
    time is 5 total line items.
    """

    return {
        "previous": "",
        "next": "",
        "results": [
            {
                "line_item_id": 1,
                "item_sku": "1 oblivion potion",
                "customer_name": "Scaramouche",
                "line_item_total": 50,
                "timestamp": "2021-01-01T00:00:00Z",
            }
        ],
    }


class Customer(BaseModel):
    customer_name: str
    character_class: str
    level: int

@router.post("/visits/{visit_id}")
def post_visits(visit_id: int, customers: list[Customer]):
    """
    Which customers visited the shop today?
    """
    print(customers)
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("""SELECT id
                                                        FROM DATE
                                                        ORDER BY id DESC
                                                        LIMIT 1"""))
        #whatever the day is
        id = result.scalar()

        customer_data = [
            {
                "customer_name": customer.customer_name,
                "customer_class": customer.character_class,
                "customer_level": customer.level,
            "time_id": id
            }
            for customer in customers
        ]
        connection.execute(sqlalchemy.text("""INSERT INTO customer_visit_table
                                           (customer_name, customer_class, customer_level, time_id)
                                           VALUES (:customer_name, :customer_class, :customer_level, :time_id)
                                           """),
                                           customer_data)

    return "OK"


@router.post("/")
def create_cart(new_cart: Customer):
    """ """
    #Customer.# implement customer stuff once getting some data.
    with db.engine.begin() as connection:
        #create order in db
        result = connection.execute(sqlalchemy.text("""INSERT INTO cart_order_table DEFAULT VALUES 
                                                    RETURNING id"""))
        order_id = result.scalar()
        #grab the most recent time period
        result = connection.execute(sqlalchemy.text("""SELECT id
                                                        FROM DATE
                                                        ORDER BY id DESC
                                                        LIMIT 1"""))
        time_id = result.scalar()

        connection.execute(sqlalchemy.text("""UPDATE cart_order_table 
                                           SET customer_class = :customer_class, 
                                           customer_level = :customer_level, 
                                           customer_name = :customer_name,
                                           transaction_occurred = :transaction_occurred,
                                           time_id = :time_id
                                           WHERE id = :order_id"""),
                            {"customer_class": new_cart.character_class, "customer_level": new_cart.level, "customer_name": new_cart.customer_name, "order_id": order_id, "transaction_occurred": False, "time_id": time_id}
                           )
    return {"cart_id": order_id}

class CartItem(BaseModel):
    quantity: int


@router.post("/{cart_id}/items/{item_sku}")
def set_item_quantity(cart_id: int, item_sku: str, cart_item: CartItem):
    """ """

    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("""SELECT id
                                           FROM potion_info_table
                                           WHERE potion_sku = :item_sku
                                           """),
                {"item_sku": item_sku})
        
        potion_id = result.scalar()

        connection.execute(sqlalchemy.text("""INSERT INTO carts (cart_id, potion_id, quantity)
            VALUES (:cart_id, :potion_id, :quantity)"""), 
            {"cart_id": cart_id, "potion_id": potion_id, "quantity": cart_item.quantity})
    return "OK"

class CartCheckout(BaseModel):
    payment: str

@router.post("/{cart_id}/checkout")
def checkout(cart_id: int, cart_checkout: CartCheckout):
    """ """

    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("""SELECT transaction_occurred 
                                                    FROM cart_order_table 
                                                    WHERE id = :order_id"""),
        {"order_id": cart_id})
        row = result.mappings().one()
        transaction_occured = row['transaction_occurred']



        result = connection.execute(sqlalchemy.text("""SELECT potion_id, quantity
                                                    FROM carts 
                                                    WHERE cart_id = :order_id"""),
        {"order_id": cart_id})


        rows = result.mappings().all()

        potion_list = []
        #gather all potions
        for row in rows:
            potion_id = row['potion_id']
            quantity = row['quantity']
            potion_list.append([potion_id, quantity])

        potion_ids = [potion[0] for potion in potion_list]

        result = connection.execute(sqlalchemy.text("""SELECT
                                                    reset_timestamp
                                                    FROM global_inventory"""))

        reset_timestamp = result.scalar()

        potion_quans = get_potion_quan(connection, reset_timestamp)

        result = connection.execute(sqlalchemy.text("""SELECT id, price, "1g_strat"
                                                    FROM potion_info_table
                                                    WHERE id IN :potion_ids"""),
                                                    {"potion_ids": tuple(potion_ids)})

        rows = result.mappings().all()

        # Create potion_info_dict with price and one_g_strat
        potion_info_dict = {row['id']: (row['price'], row['1g_strat']) for row in rows}

        # Initialize the updated dictionary
        updated_dict = []

        # Create a dictionary for potion quantities for easy lookup
        potion_quantity_dict = {pq['potion_id']: pq['quantity'] for pq in potion_quans}

        # Construct updated_dict with inventory
        for potion_id, (price, one_g_strat) in potion_info_dict.items():
            # Create a new dictionary for each potion
            potion_dict = {
                'id': potion_id,
                'price': price,
                '1g_strat': one_g_strat,
                'quantity': potion_quantity_dict.get(potion_id, 0)  # Add inventory based on potion_quantity_dict
            }
    
            updated_dict.append(potion_dict)  # Add the updated potion dictionary to the list

        print(updated_dict)  # Print to check the updated dictionary

        total_gold_paid = 0
        total_potions_bought = 0

        for potion in potion_list:
            potion_id = potion[0]
            inventory = potion[1]
            potion_info = next((item for item in updated_dict if item['id'] == potion_id), None)
            #means we are going giga strat mode
            if one_g_strat is False:
                price = 1
                connection.execute(sqlalchemy.text("""UPDATE potion_info_table
                                                   SET "1g_strat" = True
                                                   WHERE id = :potion_id"""),
                                                   {"potion_id": potion_id})
            potion.append(inventory)
            potion.append(price)
            #change in potion numbers
            #money gained from sellign that specfic potion
            potion.append(potion[1]*price)
            total_gold_paid += potion[1]*price 
            total_potions_bought += potion[1]

        if transaction_occured == False:
            # connection.execute(sqlalchemy.text("""UPDATE global_inventory 
            #                                    SET gold = gold + :gold_change"""),
            # {"gold_change": total_gold_paid})

            #ive never seen someone buy multiple potion types, but this is just incase
            for potion in potion_list:
            #     potion_id = potion[0]
            #     quantity = potion[1]
            #     price = potion[3] 
            #     connection.execute(sqlalchemy.text("""UPDATE potion_info_table
            #                                         SET inventory = inventory - :potion_num
            #                                         WHERE id = :potion_id"""),
            #                                         {"potion_num": quantity, "potion_id": potion_id})
                
                connection.execute(sqlalchemy.text("""INSERT INTO ledger_transactions
                                                    (exchange_type, linking_id, gold_difference, potion_id, potion_quantity) 
                                                    VALUES ('Potion Sell', :id, :gold_diff, :potion_id, :potion_quantity)
                                                    """),
                                                    {"id": cart_id, "gold_diff": quantity*price, "potion_id": potion_id, "potion_quantity": -1*quantity})

            connection.execute(sqlalchemy.text("""UPDATE cart_order_table 
                                               SET transaction_occurred = :transaction_occurred
                                               WHERE id = :order_id"""),
                           {"transaction_occurred": True, "order_id": cart_id})
            
            
            return {"total_potions_bought": total_potions_bought, "total_gold_paid": total_gold_paid}
        else: # This means the transaction has already happened --- concurrency error
            #still have to return the correct amount of stuff.

            return {"total_potions_bought": total_potions_bought, "total_gold_paid": total_gold_paid}