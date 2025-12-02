from mable.cargo_bidding import TradingCompany, Bid
from mable.examples import environment, fleets
from mable.transport_operation import ScheduleProposal


class MyCompany(TradingCompany):
    # Exercise 1
    # def propose_schedules(self, trades):
    #     schedules = {}
    #     scheduled_trades = []
    #     i = 0
    #     while i < len(trades):
    #         current_trade = trades[i]
    #         is_assigned = False
    #         j = 0
    #         while j < len(self._fleet) and not is_assigned:
    #             current_vessel = self._fleet[j]
    #             current_vessel_schedule = schedules.get(
    #                 current_vessel, current_vessel.schedule
    #             )
    #             new_schedule = current_vessel_schedule.copy()
    #             insertion_points = new_schedule.get_insertion_points()
    #             shortest_schedule = None
    #             for k in range(len(insertion_points)):
    #                 idx_pick_up = insertion_points[k]
    #                 insertion_point_after_idx_k = insertion_points[k:]
    #                 for m in range(len(insertion_point_after_idx_k)):
    #                     idx_drop_off = insertion_point_after_idx_k[m]
    #                     new_schedule_test = new_schedule.copy()
    #                     new_schedule_test.add_transportation(
    #                         current_trade, idx_pick_up, idx_drop_off
    #                     )
    #                     if (
    #                         shortest_schedule is None
    #                         or new_schedule_test.completion_time()
    #                         < shortest_schedule.completion_time()
    #                     ):
    #                         if new_schedule_test.verify_schedule():
    #                             shortest_schedule = new_schedule_test
    #                 if shortest_schedule is not None:
    #                     schedules[current_vessel] = shortest_schedule
    #                     scheduled_trades.append(current_trade)
    #                     is_assigned = True
    #                 j += 1
    #             i += 1
    #         return ScheduleProposal(schedules, scheduled_trades, {})

    # Exercise 2
    # def propose_schedules(self, trades):
    #     schedules = {}
    #     costs = {}
    #     scheduled_trades = []
    #     i = 0

    #     while i < len(trades):
    #         current_trade = trades[i]
    #         is_assigned = False
    #         j = 0

    #         while j < len(self._fleet) and not is_assigned:
    #             current_vessel = self._fleet[j]
    #             current_vessel_schedule = schedules.get(
    #                 current_vessel, current_vessel.schedule
    #             )
    #             new_schedule = current_vessel_schedule.copy()
    #             new_schedule.add_transportation(current_trade)

    #             if new_schedule.verify_schedule():
    #                 # Calculate loading time and costs
    #                 loading_time = current_vessel.get_loading_time(
    #                     current_trade.cargo_type, current_trade.amount
    #                 )
    #                 loading_costs = current_vessel.get_loading_consumption(loading_time)
    #                 unloading_costs = current_vessel.get_unloading_consumption(
    #                     loading_time
    #                 )

    #                 # Calculate travel costs
    #                 travel_distance = self.headquarters.get_network_distance(
    #                     current_trade.origin_port, current_trade.destination_port
    #                 )
    #                 travel_time = current_vessel.get_travel_time(travel_distance)
    #                 travel_cost = current_vessel.get_laden_consumption(
    #                     travel_time, current_vessel.speed
    #                 )

    #                 # Store total cost
    #                 costs[current_trade] = loading_costs + unloading_costs + travel_cost

    #                 # Update schedule and mark trade as assigned
    #                 schedules[current_vessel] = new_schedule
    #                 scheduled_trades.append(current_trade)
    #                 is_assigned = True

    #             j += 1
    #         i += 1

    #     return ScheduleProposal(schedules, scheduled_trades, costs)
    
        def propose_schedules(self, trades):
            schedules = {}
            costs = {}
            scheduled_trades = []

            print(f"Total trades received: {len(trades)}")

            i = 0
            while i < len(trades):
                current_trade = trades[i]
                is_assigned = False
                j = 0

                print(f"\nTrying to schedule trade {i}: {current_trade}")

                while j < len(self._fleet) and not is_assigned:
                    current_vessel = self._fleet[j]
                    current_vessel_schedule = schedules.get(current_vessel, current_vessel.schedule)
                    new_schedule = current_vessel_schedule.copy()
                    new_schedule.add_transportation(current_trade)

                    if new_schedule.verify_schedule():
                        # Calculate costs
                        loading_time = current_vessel.get_loading_time(current_trade.cargo_type, current_trade.amount)
                        loading_costs = current_vessel.get_loading_consumption(loading_time)
                        unloading_costs = current_vessel.get_unloading_consumption(loading_time)

                        travel_distance = self.headquarters.get_network_distance(
                            current_trade.origin_port, current_trade.destination_port
                        )
                        travel_time = current_vessel.get_travel_time(travel_distance)
                        travel_cost = current_vessel.get_laden_consumption(travel_time, current_vessel.speed)

                        total_cost = loading_costs + unloading_costs + travel_cost
                        costs[current_trade] = total_cost

                        # Update schedules
                        schedules[current_vessel] = new_schedule
                        scheduled_trades.append(current_trade)
                        is_assigned = True

                        print(f"Trade assigned to vessel: {current_vessel.name}")
                        print(f"Loading cost: {loading_costs:.2f}, Unloading cost: {unloading_costs:.2f}, Travel cost: {travel_cost:.2f}")
                        print(f"Total cost for this trade: {total_cost:.2f}")
                    else:
                        print(f"Vessel {current_vessel.name} cannot take this trade.")

                    j += 1

                if not is_assigned:
                    print(f"Trade {i} could NOT be scheduled on any vessel.")

                i += 1

            print(f"\nTotal trades scheduled: {len(scheduled_trades)}")
            print(f"Total cost of all scheduled trades: {sum(costs.values()):.2f}")

            return ScheduleProposal(schedules, scheduled_trades, costs)


if __name__ == "__main__":
    specifications_builder = environment.get_specification_builder(
        environment_files_path="."
    )
    fleet = fleets.example_fleet_1()
    specifications_builder.add_company(MyCompany.Data(MyCompany, fleet, "Bishal Corp"))
    sim = environment.generate_simulation(specifications_builder)
    sim.run()
