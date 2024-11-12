from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db
from src.api.inventory import get_gold_quan, get_ml_quan, get_potion_quan

#As a very basic initial logic, purchase a new small green potion barrel only if the number of potions 
#in inventory is less than 10. Always mix all available green ml if any exists. Offer up for sale in 
#the catalog only the amount of green potions that actually exist currently in inventory.

router = APIRouter(
    prefix="/barrels",
    tags=["barrels"],
    dependencies=[Depends(auth.get_api_key)],
)

class Barrel(BaseModel):
    sku: str

    ml_per_barrel: int
    potion_type: list[int]
    price: int

    quantity: int

@router.post("/deliver/{order_id}")
def post_deliver_barrels(barrels_delivered: list[Barrel], order_id: int):
    # interact with db

    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("""SELECT EXISTS
                                                    (SELECT 1 FROM barrel_order_table 
                                                    WHERE barrel_order_id = :barrel_order_id)"""), 
                                    {"barrel_order_id": order_id})
        #if the row exists, this transaction has already happened!! bad!
        row = result.scalar()
        if row == True:
            return "OK"
        else: # if no exist then go ahead and change the db!
        
            red_change = 0
            green_change = 0
            blue_change = 0
            dark_change = 0


            gold_paying = 0
            barrels_to_insert = []
            for barrel in barrels_delivered :
                gold_paying += barrel.price * barrel.quantity
                if barrel.potion_type == [1,0,0,0]:
                    red_change += barrel.ml_per_barrel * barrel.quantity
                    barrels_to_insert.append(([1,0,0,0], barrel.ml_per_barrel * barrel.quantity))  
                if barrel.potion_type == [0,1,0,0]:
                    green_change += barrel.ml_per_barrel * barrel.quantity
                    barrels_to_insert.append(([0,1,0,0], barrel.ml_per_barrel * barrel.quantity)) 
                if barrel.potion_type == [0,0,1,0]:
                    blue_change += barrel.ml_per_barrel * barrel.quantity
                    barrels_to_insert.append(([0,0,1,0], barrel.ml_per_barrel * barrel.quantity)) 
                if barrel.potion_type == [0,0,0,1]:
                    dark_change += barrel.ml_per_barrel * barrel.quantity
                    barrels_to_insert.append(([0,0,0,1], barrel.ml_per_barrel * barrel.quantity)) 


            connection.execute(sqlalchemy.text("""INSERT INTO barrel_order_table 
                                               (barrel_order_id) 
                                               VALUES 
                                               (:barrel_order_id)"""),
                               {"barrel_order_id": order_id})  

            result = connection.execute(sqlalchemy.text("""SELECT id
                                                        FROM DATE
                                                        ORDER BY id DESC
                                                        LIMIT 1"""))
            time_id = result.scalar()

        if barrels_to_insert:
            insert_values = ", ".join(
                [f"(:barrel_order_id, :time_id, '{barrel_type}', {quantity_ml})" for barrel_type, quantity_ml in barrels_to_insert]
            )

            connection.execute(sqlalchemy.text(f"""INSERT INTO barrels 
                                               (barrel_order_id, time_id, barrel_type, quantity_ml) 
                                               VALUES {insert_values}"""),
                               {"barrel_order_id": order_id, "time_id": time_id})

    
            # connection.execute(sqlalchemy.text("""UPDATE global_inventory 
            #                                    SET num_green_ml = num_green_ml + :green_change, 
            #                                    num_red_ml = num_red_ml + :red_change, 
            #                                    num_blue_ml = num_blue_ml + :blue_change, 
            #                                    num_dark_ml = num_dark_ml + :dark_change,
            #                                    gold = gold - :gold_change"""),
            #                     {"green_change": green_change, "red_change": red_change, "blue_change": blue_change,"dark_change": dark_change, "gold_change": gold_paying})
            
            connection.execute(sqlalchemy.text("""INSERT INTO ledger_transactions (exchange_type, linking_id, gold_difference, red_ml_change, green_ml_change, blue_ml_change, dark_ml_change)
                                               VALUES ('Barrel Purchase', :id, :gold_diff, :red_change, :green_change, :blue_change, :dark_change)
                                               """),
                                               {"id": order_id, "gold_diff": -1*gold_paying, "red_change": red_change, "green_change": green_change, "blue_change": blue_change, "dark_change": dark_change})
        
            print(f"barrels delievered: {barrels_delivered} order_id: {order_id}")
            return "OK"

#deal with adding dictionary stuff
def add_or_increment_item(item_list, new_item):
    for item in item_list:
        #check if the item with the same sku already exists
        if item['sku'] == new_item['sku']:
            #increment the quantity by the value of the new item
            item['quantity'] += new_item['quantity']
            return

    #if the item does not exist, add it to the list
    item_list.append(new_item)

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):

    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("""SELECT reset_timestamp, ml_capacity
                                                    FROM global_inventory"""))

        row = result.mappings().one()
        reset_timestamp = row['reset_timestamp']
        ml_capacity = row['ml_capacity']

        ml_quan = get_ml_quan(connection, reset_timestamp)

        num_red_ml = ml_quan[0]
        num_green_ml = ml_quan[1]
        num_blue_ml = ml_quan[2]
        num_dark_ml = ml_quan[3]
        ml_total = num_dark_ml + num_blue_ml + num_green_ml + num_red_ml
        gold = get_gold_quan(connection, reset_timestamp)

        result = connection.execute(sqlalchemy.text("""SELECT day, id, time
                                                        FROM DATE
                                                        ORDER BY id DESC
                                                        LIMIT 1"""))
        row = result.mappings().one()
        day = row['day']
        time = row['time']
        id = row['id']

        barrel_data = [
            {
                "barrel_price": barrel.price,
                "barrel_type": barrel.potion_type,
                "barrel_amount": barrel.ml_per_barrel,
                "time_id": id
            }
            for barrel in wholesale_catalog
        ]
        connection.execute(sqlalchemy.text("""INSERT INTO barrels_offered_table
                                            (barrel_type, barrel_price, barrel_amount, time_id)
                                            VALUES (:barrel_type, :barrel_price, :barrel_amount, :time_id)
                                            """),
                                            barrel_data)
        buying_list = []

        efficiency_list = []

        for barrel in wholesale_catalog:
            efficiency_list.append(barrel)

        potion_type_map = {
            (1, 0, 0, 0): "red",
            (0, 1, 0, 0): "green",
            (0, 0, 1, 0): "blue",
            (0, 0, 0, 1): "dark"
        }

        efficiency_list.sort(
            key=lambda barrel: (
                -(barrel.ml_per_barrel / barrel.price),  #efficiency
                potion_type_map.get(tuple(barrel.potion_type), "") != "blue",
                potion_type_map.get(tuple(barrel.potion_type), "") != "green"
            )
        )

        print(efficiency_list)

        while ml_total <= ml_capacity and gold > 0:
            purchased_any = False
            # for potion_type, percentage in ml_compare_list:
            for barrel in efficiency_list:

                #handle buying based having limits based on current max capacity
                if barrel.potion_type == [1,0,0,0] and "MINI" not in barrel.sku and (day != "Edgeday" or (day != "Soulday" and time >= 20) or gold > 1000) and num_red_ml < (2000 + 1250*(ml_capacity/10000)):
                    if barrel.quantity > 0 and barrel.ml_per_barrel + ml_total <= ml_capacity and gold >= barrel.price:
                        sku = barrel.sku
                        barrel.quantity -= 1
                        gold -= barrel.price
                        ml_total += barrel.ml_per_barrel
                        num_red_ml += barrel.ml_per_barrel
                        add_or_increment_item(buying_list, {'sku': sku, 'quantity': 1})
                        purchased_any = True
                elif barrel.potion_type == [0,1,0,0] and "MINI" not in barrel.sku and (day != "Bloomday" or (day != "Edgeday" and time >= 20) or gold > 1000) and num_green_ml < (2000 + 1250*(ml_capacity/10000)):
                    if barrel.quantity > 0 and barrel.ml_per_barrel + ml_total <= ml_capacity and gold >= barrel.price:
                        sku = barrel.sku
                        barrel.quantity -= 1
                        gold -= barrel.price
                        ml_total += barrel.ml_per_barrel
                        num_green_ml += barrel.ml_per_barrel
                        add_or_increment_item(buying_list, {'sku': sku, 'quantity': 1})
                        purchased_any = True
                elif barrel.potion_type == [0,0,1,0] and "MINI" not in barrel.sku and (day != "Arcanaday" or (day != "Bloomday" and time >= 20) or gold > 1000) and num_blue_ml < (2000 + 1250*(ml_capacity/10000)):
                    if barrel.quantity > 0 and barrel.ml_per_barrel + ml_total <= ml_capacity and gold >= barrel.price:
                        sku = barrel.sku
                        barrel.quantity -= 1
                        gold -= barrel.price
                        ml_total += barrel.ml_per_barrel
                        num_blue_ml += barrel.ml_per_barrel
                        add_or_increment_item(buying_list, {'sku': sku, 'quantity': 1})
                        purchased_any = True
                elif barrel.potion_type == [0,0,0,1] and "MINI" not in barrel.sku and num_dark_ml < (2000 + 1250*(ml_capacity/10000)):
                    if barrel.quantity > 0 and barrel.ml_per_barrel + ml_total <= ml_capacity and gold >= barrel.price:
                        sku = barrel.sku
                        barrel.quantity -= 1
                        gold -= barrel.price
                        ml_total += barrel.ml_per_barrel
                        num_dark_ml += barrel.ml_per_barrel
                        add_or_increment_item(buying_list, {'sku': sku, 'quantity': 1})
                        purchased_any = True

            if not purchased_any:
                break

        return buying_list