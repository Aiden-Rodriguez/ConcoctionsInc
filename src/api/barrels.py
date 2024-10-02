from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db

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
        result = connection.execute(sqlalchemy.text("SELECT num_green_ml, gold FROM global_inventory"))
        row = result.mappings().one()  # Using mappings to access the columns by name

        # Extract values from the row
        
        num_green_ml = row['num_green_ml']
        gold = row['gold']

        for barrel in barrels_delivered :
            gold -= barrel.price * barrel.quantity
            num_green_ml += barrel.ml_per_barrel * barrel.quantity
        

        with db.engine.begin() as connection:
            connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_green_ml = :additional_green_ml, gold = :gold;"),
                                {"additional_green_ml": num_green_ml, "gold": gold})
    """ """
    #print(f"barrels delievered: {barrels_delivered} order_id: {order_id}")

    return "OK"

#deal with adding dictionary stuff
def add_or_increment_item(item_list, new_item):
    for item in item_list:
        #check if the item with the same sku already exists
        if item['sku'] == new_item['sku']:
            #increment the quantity by the value of the new item
            item['quantity'] += new_item['quantity']
            return  # Exit the function after updating

    # If the item does not exist, add it to the list
    item_list.append(new_item)

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    # Interact with db
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT num_green_potions, num_blue_potions, num_red_potions, num_dark_potions, num_green_ml, num_blue_ml, num_red_ml, num_dark_ml, gold, ml_capacity FROM global_inventory"))

        row = result.mappings().one()  # Using mappings to access the columns by name

        # Extract values from the row
        num_green_potions = row['num_green_potions']
        num_blue_potions = row['num_blue_potions']
        num_red_potions = row['num_red_potions']
        num_dark_potions = row['num_dark_potions']
        num_green_ml = row['num_green_ml']
        num_blue_ml = row['num_blue_ml']
        num_red_ml = row['num_red_ml']
        num_dark_ml = row['num_dark_ml']
        ml_total = num_dark_ml + num_blue_ml + num_green_ml + num_red_ml
        ml_capacity = row['ml_capacity']
        gold = row['gold']

        buying_list = []

        # List to keep track of potion counts and ml counts
        potion_compare_list = [num_red_potions, num_green_potions, num_blue_potions, num_dark_potions]
        ml_compare_list = [num_red_ml, num_green_ml, num_blue_ml, num_dark_ml]

        loop_counter = 0
        max_iterations = 1000  # Arbitrary limit to prevent infinite loop

        while ml_total < ml_capacity and gold > 0:
            loop_counter += 1
            if loop_counter > max_iterations:
                return "Not Sigma loop"
            
            # Get indexes of potion type with the lowest counts
            min_value_potion = min(potion_compare_list)
            min_indexes_potion = [i for i, num in enumerate(potion_compare_list) if num == min_value_potion]

            purchased_any = False

            # Priority buying based on potion types
            for barrel in wholesale_catalog:
                # Determine the current potion type and its corresponding index
                potion_type_index = -1
                if barrel.potion_type == [1, 0, 0, 0]:  # Red
                    potion_type_index = 0
                elif barrel.potion_type == [0, 1, 0, 0]:  # Green
                    potion_type_index = 1
                elif barrel.potion_type == [0, 0, 1, 0]:  # Blue
                    potion_type_index = 2
                elif barrel.potion_type == [0, 0, 0, 1]:  # Dark
                    potion_type_index = 3

                # Handle buying based on potion availability and lowest potion count
                if potion_type_index in min_indexes_potion:
                    while barrel.quantity > 0 and ml_total + barrel.ml_per_barrel <= ml_capacity and gold >= barrel.price:
                        # Adjust ML tracking based on potion type
                        if potion_type_index == 0:  # Red
                            if num_red_ml < 500:
                                sku = barrel.sku
                                barrel.quantity -= 1
                                gold -= barrel.price
                                ml_total += barrel.ml_per_barrel
                                num_red_ml += barrel.ml_per_barrel
                                add_or_increment_item(buying_list, {'sku': sku, 'quantity': 1})
                                purchased_any = True
                        elif potion_type_index == 1:  # Green
                            if num_green_ml < 500:
                                sku = barrel.sku
                                barrel.quantity -= 1
                                gold -= barrel.price
                                ml_total += barrel.ml_per_barrel
                                num_green_ml += barrel.ml_per_barrel
                                add_or_increment_item(buying_list, {'sku': sku, 'quantity': 1})
                                purchased_any = True
                        elif potion_type_index == 2:  # Blue
                            if num_blue_ml < 500:
                                sku = barrel.sku
                                barrel.quantity -= 1
                                gold -= barrel.price
                                ml_total += barrel.ml_per_barrel
                                num_blue_ml += barrel.ml_per_barrel
                                add_or_increment_item(buying_list, {'sku': sku, 'quantity': 1})
                                purchased_any = True
                        elif potion_type_index == 3:  # Dark
                            if num_dark_ml < 500:
                                sku = barrel.sku
                                barrel.quantity -= 1
                                gold -= barrel.price
                                ml_total += barrel.ml_per_barrel
                                num_dark_ml += barrel.ml_per_barrel
                                add_or_increment_item(buying_list, {'sku': sku, 'quantity': 1})
                                purchased_any = True
            
            # Break the loop if no barrels were purchased in this iteration
            if not purchased_any:
                break

        return buying_list

                
        # if num_green_potions < 10 :
        #     #check all barrels for green
        #     for barrel in wholesale_catalog :
        #         # for green barrels
        #         if barrel.potion_type == [0,1,0,0]:
        #             #buy barrels until out of money or none are left
        #             while barrel.price <= gold and barrel.quantity > 0:
        #                 sku = barrel.sku
        #                 quantity += 1
        #                 barrel.quantity -= 1
        #                 gold -= barrel.price
    # return [
    #     {
    #             "sku": sku,
    #             "quantity": quantity,
    #     }
    # ]