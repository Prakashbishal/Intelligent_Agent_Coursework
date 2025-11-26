from mable.cargo_bidding import TradingCompany
from mable.examples import environment, fleets, shipping, companies


class MyCompany(TradingCompany):

    def inform(self, trades, *args, **kwargs):
        # We are not bidding in this exercise
        print("[inform] Not bidding this round.")
        return []

    def receive(self, contracts, auction_ledger=None, *args, **kwargs):
        competitor_name = "Arch Enemy Ltd."

        # Safely find competitor fleet
        competitors = [c for c in self.headquarters.get_companies() if c.name == competitor_name]
        if not competitors:
            print(f"[receive] Competitor '{competitor_name}' not found.")
            return

        competitor_fleet = competitors.pop().fleet
        competitor_won_contracts = auction_ledger.get(competitor_name, [])

        print(f"\n[receive] Found {len(competitor_won_contracts)} contracts won by {competitor_name}.")

        # Loop over each contract they won
        for contract in competitor_won_contracts:
            trade = contract.trade
            payment = contract.payment
            best_cost = float("inf")

            # Try all vessels to find the one with minimum predicted cost
            for vessel in competitor_fleet:
                predicted_cost = self.predict_cost(vessel, trade)
                if predicted_cost < best_cost:
                    best_cost = predicted_cost

            if best_cost > 0:
                profit_factor = payment / best_cost
                print(
                    f"  Trade {trade.origin_port}->{trade.destination_port}: "
                    f"Payment={payment:.2f}, Predicted Cost={best_cost:.2f}, "
                    f"Estimated Profit Factor={profit_factor:.3f}"
                )
            else:
                print(f"  Trade {trade.origin_port}->{trade.destination_port}: Skipped (invalid cost)")

    def predict_cost(self, vessel, trade):
        """Estimate the cost of performing a trade for a given vessel."""
        loading_time = vessel.get_loading_time(trade.cargo_type, trade.amount)
        loading_cost = vessel.get_loading_consumption(loading_time)
        unloading_cost = vessel.get_unloading_consumption(loading_time)
        travel_distance = self.headquarters.get_network_distance(trade.origin_port, trade.destination_port)
        travel_time = vessel.get_travel_time(travel_distance)
        travel_cost = vessel.get_laden_consumption(travel_time, vessel.speed)

        total_cost = loading_cost + unloading_cost + travel_cost
        return total_cost


def build_specification():
    specifications_builder = environment.get_specification_builder(
        fixed_trades=shipping.example_trades_1()
    )
    fleet = fleets.example_fleet_1()

    # Add your company (observer)
    specifications_builder.add_company(MyCompany.Data(MyCompany, fleet, MyCompany.__name__))

    # Add competitor company
    specifications_builder.add_company(
        companies.MyArchEnemy.Data(companies.MyArchEnemy, fleets.example_fleet_2(), "Arch Enemy Ltd.")
    )

    sim = environment.generate_simulation(
        specifications_builder,
        show_detailed_auction_outcome=True
    )
    sim.run()


if __name__ == '__main__':
    build_specification()
