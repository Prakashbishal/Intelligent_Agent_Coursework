from mable.cargo_bidding import TradingCompany, Bid
from mable.examples import environment, fleets
from mable.transport_operation import ScheduleProposal


class MyCompany(TradingCompany):
    
    def propose_schedules(self, trades):
        schedules = {}
        scheduled_trades = []
        for trade in trades:
            for vessel in self._fleet:
                new_schedule = vessel.schedule.copy()
                new_schedule.add_transportation(trade)
                if new_schedule.verify_schedule():
                    schedules[vessel] = new_schedule
                    scheduled_trades.append(trade)
                    break
        return ScheduleProposal(schedules, scheduled_trades, {})
    
    def inform(self, trades, *args, **kwargs):
        print(f"Received {len(trades)} trades")
        bids = []
        for t in trades:
            print(f"Bidding on {t.origin_port.name} → {t.destination_port.name}")
            bids.append(Bid(amount=2000, trade=t))
        return bids

    def receive(self, contracts, *args, **kwargs):
        print(f"Won {len(contracts)} trades")
        trades = [c.trade for c in contracts]
        proposal = self.propose_schedules(trades)
        print("Applying schedule:", proposal.schedules)
        self.apply_schedules(proposal.schedules)

if __name__ == "__main__":
    specifications_builder = environment.get_specification_builder(
        environment_files_path="."
    )
    fleet = fleets.example_fleet_1()
    specifications_builder.add_company(MyCompany.Data(MyCompany, fleet, "Bishal Corp"))
    sim = environment.generate_simulation(specifications_builder)
    sim.run()
