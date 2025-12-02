from mable.cargo_bidding import TradingCompany
from mable.examples import environment, fleets, shipping
from mable.transport_operation import Bid, ScheduleProposal


class MyCompany(TradingCompany):

    def __init__(self, fleet, name):
        super().__init__(fleet, name)
        self._future_trades = None  # Stores trades for the next auction

    def pre_inform(self, trades, time):
        self._future_trades = trades
        print(f"[pre_inform] Storing {len(trades)} future trades for next auction.")

    def inform(self, trades, *args, **kwargs):
        print(f"[inform] Bidding on {len(trades)} current trades.")
        proposed_scheduling = self.propose_schedules(trades)
        scheduled_trades = proposed_scheduling.scheduled_trades
        self._current_scheduling_proposal = proposed_scheduling

        trades_and_costs = [
            (trade, proposed_scheduling.costs[trade] if trade in proposed_scheduling.costs else 0)
            for trade in scheduled_trades
        ]
        bids = [Bid(amount=cost, trade=trade) for trade, cost in trades_and_costs]

        print(f"[inform] Created {len(bids)} bids:")
        for bid in bids:
            print(f"  Trade {bid.trade.origin_port}->{bid.trade.destination_port}, Bid amount: {bid.amount:.2f}")

        self._future_trades = None  # Forget future trades after bidding
        return bids

    def receive(self, contracts, auction_ledger=None, *args, **kwargs):
        trades = [contract.trade for contract in contracts]
        print(f"[receive] Applying {len(trades)} won trades.")
        scheduling_proposal = self.find_schedules(trades)
        self.apply_schedules(scheduling_proposal.schedules)

    def propose_schedules(self, trades):
        schedules = {}
        costs = {}
        scheduled_trades = []

        for vessel in self._fleet:
            print(f"\n[propose_schedules] Evaluating vessel: {vessel.name}")

            best_trade = None
            min_distance = float("inf")

            for current_trade in trades:
                if not current_trade:
                    continue    

                print(f"  Considering current trade: {current_trade.origin_port}->{current_trade.destination_port}")

                # Case 1: Future trades exist
                if self._future_trades:
                    # Find the closest future trade
                    for future_trade in self._future_trades:
                        distance = self.headquarters.get_network_distance(
                            current_trade.destination_port,
                            future_trade.origin_port
                        )
                        print(f"    Distance to future trade {future_trade.origin_port}->{future_trade.destination_port}: {distance:.2f}")

                        if distance < min_distance:
                            min_distance = distance
                            best_trade = current_trade

                # Case 2: No future trades, just pick current trade
                else:
                    best_trade = current_trade
                    min_distance = 0
                    break


            if best_trade:
                print(f"  Selected trade for vessel {vessel.name}: {best_trade.origin_port}->{best_trade.destination_port}, Closest distance to future trade: {min_distance:.2f}")
                new_schedule = schedules.get(vessel, vessel.schedule.copy())
                new_schedule.add_transportation(best_trade)

                if new_schedule.verify_schedule():
                    schedules[vessel] = new_schedule
                    scheduled_trades.append(best_trade)
                    costs[best_trade] = self.predict_cost(vessel, best_trade)
                    print(f"    Predicted cost: {costs[best_trade]:.2f}")

        return ScheduleProposal(schedules, scheduled_trades, costs)

    def predict_cost(self, vessel, trade):
        loading_time = vessel.get_loading_time(trade.cargo_type, trade.amount)
        loading_cost = vessel.get_loading_consumption(loading_time)
        unloading_cost = vessel.get_unloading_consumption(loading_time)
        travel_distance = self.headquarters.get_network_distance(trade.origin_port, trade.destination_port)
        travel_time = vessel.get_travel_time(travel_distance)
        travel_cost = vessel.get_laden_consumption(travel_time, vessel.speed)
        return loading_cost + unloading_cost + travel_cost

    def find_schedules(self, trades):
        schedules = {}
        scheduled_trades = []

        for trade in trades:
            is_assigned = False
            for vessel in self._fleet:
                if is_assigned:
                    break
                new_schedule = schedules.get(vessel, vessel.schedule.copy())
                new_schedule.add_transportation(trade)
                if new_schedule.verify_schedule():
                    schedules[vessel] = new_schedule
                    scheduled_trades.append(trade)
                    is_assigned = True
        return ScheduleProposal(schedules, scheduled_trades, {})


def build_specification():
    specifications_builder = environment.get_specification_builder(fixed_trades=shipping.example_trades_1())
    fleet = fleets.example_fleet_1()
    specifications_builder.add_company(MyCompany.Data(MyCompany, fleet, "Bishal Corp"))
    sim = environment.generate_simulation(specifications_builder, show_detailed_auction_outcome=True)
    sim.run()


if __name__ == "__main__":
    build_specification()





