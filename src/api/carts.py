from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
from enum import Enum
import sqlalchemy
from src import database as db

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
    return "OK"


@router.post("/")
def create_cart(new_cart: Customer):
    """ """
    #Customer.# implement customer stuff once getting some data.
    with db.engine.begin() as connection:
        #create order in db
        result = connection.execute(sqlalchemy.text("INSERT INTO order_table DEFAULT VALUES RETURNING id"))
        order_id = result.scalar()
        result = connection.execute(sqlalchemy.text("SELECT day, time FROM date"))
        row = result.mappings().one()
        day = row['day']
        time = row['time']
        connection.execute(sqlalchemy.text("UPDATE order_table SET customer_class = :customer_class, customer_level = :customer_level, customer_name = :customer_name, day = :day, time = :time, transaction_occurred = :transaction_occurred WHERE id = :order_id"),
                            {"customer_class": new_cart.character_class, "customer_level": new_cart.level, "customer_name": new_cart.customer_name, "order_id": order_id, "time": time, "day": day, "transaction_occurred": False}
                           )
    return {"cart_id": order_id}

class CartItem(BaseModel):
    quantity: int


@router.post("/{cart_id}/items/{item_sku}")
def set_item_quantity(cart_id: int, item_sku: str, cart_item: CartItem):
    """ """
    query = f"UPDATE order_table SET {item_sku} = :quantity WHERE id = :order_id"
    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text(query),
                {"order_id": cart_id, "quantity": cart_item.quantity}
                )
    return "OK"


class CartCheckout(BaseModel):
    payment: str

@router.post("/{cart_id}/checkout")
def checkout(cart_id: int, cart_checkout: CartCheckout):
    """ """

    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT transaction_occurred FROM order_table WHERE id = :order_id"),
        {"order_id": cart_id})
        row = result.mappings().one()
        transaction_occured = row['transaction_occurred']

        result = connection.execute(sqlalchemy.text("SELECT num_green_potions, num_red_potions, num_blue_potions, num_dark_potions FROM order_table WHERE id = :order_id"),
        {"order_id": cart_id})


        row = result.mappings().one()  # Using mappings to access the columns by name
        num_green_potions = row['num_green_potions']
        num_blue_potions = row['num_blue_potions']
        num_red_potions = row['num_red_potions']
        num_dark_potions = row['num_dark_potions']

        total_potions_bought = 0
        total_gold_paid = 0
            
        while num_red_potions >= 1:
            num_red_potions -= 1
            total_potions_bought += 1
            total_gold_paid += 50
        while num_green_potions >= 1:
            num_green_potions -= 1
            total_potions_bought += 1
            total_gold_paid += 50
        while num_blue_potions >= 1:
            num_blue_potions -= 1
            total_potions_bought += 1
            total_gold_paid += 50
        while num_dark_potions >= 1:
            num_dark_potions -= 1
            total_potions_bought += 1
            total_gold_paid += 50

        if transaction_occured == False:
            result = connection.execute(sqlalchemy.text("SELECT gold, num_green_potions, num_red_potions, num_blue_potions, num_dark_potions FROM global_inventory"))

            row = result.mappings().one()  # Using mappings to access the columns by name
            gold = row['gold']
            inv_green_potions = row['num_green_potions']
            inv_blue_potions = row['num_blue_potions']
            inv_red_potions = row['num_red_potions']
            inv_dark_potions = row['num_dark_potions']
            # Extract values from the row

            buying_list = []

            potions_ud_g = inv_green_potions - row['num_green_potions']
            potions_ud_b = inv_blue_potions - row['num_blue_potions']
            potions_ud_r = inv_red_potions - row['num_red_potions']
            potions_ud_d = inv_dark_potions - row['num_dark_potions']

            gold += total_gold_paid
            connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_green_potions = :num_green_potions,  num_red_potions = :num_red_potions, num_blue_potions = :num_blue_potions, num_dark_potions = :num_dark_potions, gold = :gold;"),
            {"num_green_potions": potions_ud_g, "num_red_potions": potions_ud_r, "num_blue_potions": potions_ud_b, "num_dark_potions": potions_ud_d, "gold": gold})

            print(cart_checkout)

            connection.execute(sqlalchemy.text("UPDATE order_table SET transaction_occurred = :transaction_occurred WHERE id = :order_id"),
                           {"transaction_occurred": True, "order_id": cart_id})
            return {"total_potions_bought": total_potions_bought, "total_gold_paid": total_gold_paid}
        else: # This means the transaction has already happened --- concurrency error
            #still have to return the correct amount of stuff.

            return {"total_potions_bought": total_potions_bought, "total_gold_paid": total_gold_paid}