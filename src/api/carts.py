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
    # query = f"UPDATE cart_order_table SET {item_sku} = :quantity WHERE id = :order_id"

    # with db.engine.begin() as connection:
    #     connection.execute(sqlalchemy.text(query),
    #             {"order_id": cart_id, "quantity": cart_item.quantity}
    #             )

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


        rows = result.fetchall()
        
        pots = []
        #where 0 is the potion id, 1 is the quantity
        for row in rows:
            pots.append([row[0], row[1]])

        potion_ids = [pot[0] for pot in pots]

        result = connection.execute(sqlalchemy.text("""SELECT id, potion_sku
            FROM potion_info_table
            WHERE id IN :potion_ids"""), 
            {"potion_ids": tuple(potion_ids)})

        rows = result.fetchall()

        sku_quantity_mapping = {
            row[1]: pots[potion_ids.index(row[0])][1]
            for row in rows
        }

        #do it the stupid way for now
        num_green_potions = sku_quantity_mapping.get("green", 0)
        num_blue_potions = sku_quantity_mapping.get("blue", 0)
        num_red_potions = sku_quantity_mapping.get("red", 0)
        num_dark_potions = sku_quantity_mapping.get("dark", 0)

        total_potions_bought = 0
        total_potions_bought_r = 0
        total_potions_bought_g = 0
        total_potions_bought_b = 0
        total_potions_bought_d = 0
        total_gold_paid = 0
            
        while num_red_potions >= 1:
            num_red_potions -= 1
            total_potions_bought += 1
            total_gold_paid += 50
            total_potions_bought_r += 1
        while num_green_potions >= 1:
            num_green_potions -= 1
            total_potions_bought += 1
            total_gold_paid += 50
            total_potions_bought_g += 1
        while num_blue_potions >= 1:
            num_blue_potions -= 1
            total_potions_bought += 1
            total_gold_paid += 50
            total_potions_bought_b += 1
        while num_dark_potions >= 1:
            num_dark_potions -= 1
            total_potions_bought += 1
            total_gold_paid += 50
            total_potions_bought_d += 1

        if transaction_occured == False:
            connection.execute(sqlalchemy.text("""UPDATE global_inventory 
                                               SET gold = gold + :gold_change"""),
            {"gold_change": total_gold_paid})

            #kinda monkey mode but it works for now
            connection.execute(sqlalchemy.text("""
                UPDATE potion_info_table 
                    SET inventory = inventory - CASE 
                    WHEN potion_sku = 'red' THEN :num_red_potions_bought 
                    WHEN potion_sku = 'green' THEN :num_green_potions_bought 
                    WHEN potion_sku = 'blue' THEN :num_blue_potions_bought 
                    WHEN potion_sku = 'dark' THEN :num_dark_potions_bought 
                    ELSE 0 
                END
                WHERE potion_sku IN ('red', 'green', 'blue', 'dark')"""), 
                {"num_red_potions_bought": total_potions_bought_r, "num_green_potions_bought": total_potions_bought_g, "num_blue_potions_bought": total_potions_bought_b, "num_dark_potions_bought": total_potions_bought_d})

            print(cart_checkout)

            connection.execute(sqlalchemy.text("""UPDATE cart_order_table 
                                               SET transaction_occurred = :transaction_occurred
                                               WHERE id = :order_id"""),
                           {"transaction_occurred": True, "order_id": cart_id})
            
            return {"total_potions_bought": total_potions_bought, "total_gold_paid": total_gold_paid}
        else: # This means the transaction has already happened --- concurrency error
            #still have to return the correct amount of stuff.

            return {"total_potions_bought": total_potions_bought, "total_gold_paid": total_gold_paid}