# This file takes the decision variable result Z from the CPLEX program
# and creates milk-runs using nearest neighbour logic.

import pandas as pd
import simplejson as json

z_df: pd.DataFrame = pd.read_csv("z.csv", names=['P', 'W', 'S', 'T', 'Value'])
num_trucks_df = pd.read_csv("num_trucks.csv", names=['W', 'S', 'T', 'Value'])

truck_capacity = 40

stores_nearest_neighbours = {
    1: [7, 2, 9, 10, 5, 4, 8, 3, 6],
    2: [7, 10, 1, 5, 8, 9, 4, 3, 6],
    3: [6, 4, 5, 8, 7, 9, 10, 2, 1],
    4: [5, 9, 3, 7, 6, 8, 2, 1, 10],
    5: [4, 7, 8, 3, 9, 2, 10, 6, 1],
    6: [3, 5, 4, 8, 7, 9, 10, 2, 1],
    7: [2, 5, 10, 1, 9, 8, 4, 3, 6],
    8: [5, 10, 7, 3, 2, 6, 4, 9, 1],
    9: [4, 7, 5, 1, 2, 3, 8, 10, 6],
    10: [2, 7, 8, 5, 1, 4, 9, 3, 6],
}

warehouses_nearest_neighbours = {
    1: [1, 9, 7, 2, 5, 10, 4, 8, 3, 6],
    2: [8, 10, 5, 3, 6, 7, 2, 4, 9, 1]

}

num_stores = 10


class AllRunsInTimeDuringPeriod:

    def __init__(self, time) -> None:
        super().__init__()
        self.time = time
        self.collection_of_runs = []

    time: int
    collection_of_runs: []


class CollectionOfRuns(json.JSONEncoder):

    def __init__(self, warehouse) -> None:
        super().__init__()
        self.warehouse = warehouse
        self.runs = [[]]

    # Runs from warehouse
    warehouse: int
    runs: [[]]


class Shipment:

    def __init__(self, store, amount) -> None:
        super().__init__()
        self.store = store
        self.amount = amount

    store: int
    amount: int


class ComplexEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, AllRunsInTimeDuringPeriod):
            return {'time': obj.time, 'collection_of_runs': obj.collection_of_runs}
        if isinstance(obj, CollectionOfRuns):
            return {'warehouse': obj.warehouse, 'runs': obj.runs}
        if isinstance(obj, Shipment):
            return {'store': obj.store, 'amount': obj.amount}
        return json.JSONEncoder.default(self, obj)


def main():
    result = []  # Collection of AllRunsInTimeDuringPeriod
    for t in range(1, 11):
        all_runs_in_period_t = AllRunsInTimeDuringPeriod(t)
        for warehouse in range(1, 3):
            satisfied_demand = {
                1: 0,
                2: 0,
                3: 0,
                4: 0,
                5: 0,
                6: 0,
                7: 0,
                8: 0,
                9: 0,
                10: 0
            }

            warehouse_nearest_neighbours = warehouses_nearest_neighbours[warehouse]
            warehouse_neighbour_index = 0
            collection_of_runs = CollectionOfRuns(warehouse)
            while warehouse_neighbour_index < num_stores:
                next_closest_store_to_warehouse = warehouse_nearest_neighbours[warehouse_neighbour_index]
                nearest_neighbours_to_current_store = stores_nearest_neighbours[next_closest_store_to_warehouse]

                store_closest_to_current_store_index = 0
                unfulfilled_shipment_amount = truck_capacity
                current_run = []  # list of shipments

                while store_closest_to_current_store_index < num_stores - 1:
                    potential_next_store = nearest_neighbours_to_current_store[store_closest_to_current_store_index]
                    all_product_shipped_to_next_stop = z_df.query(
                        'W == ' + str(warehouse) + ' and S == ' + str(potential_next_store) + ' and T == ' + str(t))
                    num_to_ship = all_product_shipped_to_next_stop['Value'].sum() - satisfied_demand[potential_next_store]
                    if num_to_ship == 0:
                        store_closest_to_current_store_index += 1
                        continue
                    if num_to_ship > unfulfilled_shipment_amount:
                        satisfied_demand[potential_next_store] += unfulfilled_shipment_amount
                        shipment = Shipment(potential_next_store, unfulfilled_shipment_amount)
                        current_run.append(shipment)
                        if len(collection_of_runs.runs) == 1 and len(collection_of_runs.runs[0]) == 0:
                            collection_of_runs.runs[0] = current_run
                        else:
                            collection_of_runs.runs.append(current_run)
                        current_run = []
                        store_closest_to_current_store_index = num_stores
                        unfulfilled_shipment_amount = truck_capacity
                        # Do not increment store_closest_to_current_store_index
                        continue
                    unfulfilled_shipment_amount -= num_to_ship
                    shipment = Shipment(potential_next_store, num_to_ship)
                    current_run.append(shipment)
                    satisfied_demand[potential_next_store] = num_to_ship
                    store_closest_to_current_store_index += 1
                if len(current_run) > 0:
                    collection_of_runs.runs.append(current_run)
                warehouse_neighbour_index += 1
            all_runs_in_period_t.collection_of_runs.append(collection_of_runs)
        result.append(all_runs_in_period_t)
    return result


if __name__ == '__main__':
    res = main()
    json_res = json.dumps(res, sort_keys=True, cls=ComplexEncoder)
    with open("Output.txt", "w") as text_file:
        text_file.write(json_res)
