class strategyhandlerbase():
    pass

class StrategyHandlerZerroloss(strategyhandlerbase):
    def __init__(self):
        pass


    # def handle(self,strategyDF)-> DataFrame :
    #     pass

    def handleStrategy(self,strategy_data_df):
        # zerrolossstrategyestimator = zerrolossstrategyestimator()

        # _symbol = 'SAVA'
        # filename = "output_zerrowloss_{}.xlsx".format(_symbol)

        # dataDF = requester.getstrategydata(symbol=_symbol.upper())
        # dfhandled =self.handle(dfhandled )

        # Filter out non-tradable strategies (NaN values from zero-sum cases)
        strategy_data_df = strategy_data_df.dropna(subset=['year_interest_of_strategy'])

        strategy_data_df=strategy_data_df[(strategy_data_df['year_interest_of_strategy'] > 60) &
                            (strategy_data_df['year_interest_of_strategy'] < 50000) ]



        strategy_data_df = strategy_data_df.sort_values(by=['year_interest_of_strategy']).head(10)


        return strategy_data_df