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
        result = connection.execute(sqlalchemy.text("SELECT num_green_potions, num_green_ml, gold FROM global_inventory"))

    """ """
    print(f"barrels delievered: {barrels_delivered} order_id: {order_id}")

    return "OK"

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    #interact with db

    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT num_green_potions, num_green_ml, gold FROM global_inventory"))

        row = result.mappings().one()  # Using mappings to access the columns by name

        # Extract values from the row
        num_green_potions = row['num_green_potions']
        num_green_ml = row['num_green_ml']
        gold = row['gold']

        sku = ""
        quantity = 0
        # if  less than 10 pots, buy a barrel
        # pretty sure 100ml = 1 pot ..?
        if num_green_potions < 10 :
            #check all barrels for green
            for barrel in wholesale_catalog :
                if barrel.potion_type == [1] and barrel.sku == "SMALL_GREEN_BARREL":
                    if barrel.price <= gold and barrel.quantity > 0:
                        sku = "SMALL_GREEN_BARREL"
                        quantity += 1
                        barrel.quantity -= 1
                        gold -= barrel.price


        # #updating database with transaction
        # with db.engine.begin() as connection:
        #     connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_green_ml = :100, gold = :50"))
        return [sku, quantity]
    """ """

    # return [
    #     {
    #         "sku": "SMALL_GREEN_BARREL",
    #         "quantity": 1,
    #     }
    # ]

    # return [
    #     {
    #         "sku": "SMALL_RED_BARREL",
    #         "quantity": 1,
    #     }
    # ]