from itertools import count
from brownie import config, Wei, reverts, Contract
from useful_methods import genericStateOfVault, genericStateOfStrat
from eth_abi import encode_single, encode_abi
import random
import brownie

def test_saviour(
    YearnCoinSafeSaviour,
    coin_join,
    c_ratio_setter,
    system_coin_oracle,
    liquidation_engine,
    oracle_relayer,
    safe_manager,
    saviour_registry,
    vault,
    accounts,
    strategist
):
    strategist.deploy(
        YearnCoinSafeSaviour, 
        coin_join,          # coin join
        c_ratio_setter,     # cratio setter
        system_coin_oracle, # rai oracle
        liquidation_engine, # liqudiation engine
        oracle_relayer,     # oracle relayer
        safe_manager,       # safe manager
        saviour_registry,    # saviour registry
        vault,              # vault
        1e18,               # keeper payout
        1e18                # minKeeperPayoutValue
    )

def test_normal_activity(
    rai,
    Strategy,
    crRai,
    fRai,
    chain,
    whale,
    gov,
    strategist,
    rando,
    vault,
    saviour,
    strategy,
    fn_isolation,
    liquidation_engine,
    safe_manager,
    accounts
):
    starting_balance = rai.balanceOf(strategist)
    currency = rai
    decimals = currency.decimals()

    # Configure Vault
    deposit_limit = 1_000_000_000 * (10 ** (decimals))
    debt_ratio = 10_000
    vault.addStrategy(strategy, debt_ratio, 0, 2 ** 256 - 1, 500, {"from": gov})
    vault.setDepositLimit(deposit_limit, {"from": gov})

    assert deposit_limit == vault.depositLimit()

    # our humble strategist deposits some test funds
    rai.approve(saviour, 2 ** 256 - 1, {"from": strategist})
    depositAmount = 100 * (10 ** (decimals))
    safe_manager.openSAFE(encode_single('bytes32', b'ETH-A'),strategist.address,{"from":strategist})
    safe_id = safe_manager.firstSAFEID(strategist)
    liquidation_engine = Contract("0x27Efc6FFE79692E0521E7e27657cF228240A06c2")
    admin = accounts.at("0xa57A4e6170930ac547C147CdF26aE4682FA8262E", force=True)
    liquidation_engine.connectSAFESaviour(saviour,{'from':admin})
    saviour.deposit(encode_single('bytes32', b'ETH-A'), safe_id, depositAmount, {"from": strategist}) 

    #vault.deposit(depositAmount, {"from": strategist})

    assert strategy.estimatedTotalAssets() == 0
    chain.mine(1)
    assert strategy.harvestTrigger(1) == True
    strategy.harvest({"from": strategist})

    assert (
        strategy.estimatedTotalAssets() >= depositAmount * 0.9
    )  # losing some dust is ok

    print("After harvest 1 ... ")
    status = strategy.lendStatuses()
    form = "{:.2%}"
    formS = "{:,.0f}"
    for j in status:
        print(
            f"Lender: {j[0]}, Deposits: {formS.format(j[1]/1e18)}, APR: {form.format(j[2]/1e18)}"
        )

    # Add whale size deposits
    rai.approve(saviour, 2 ** 256 - 1, {"from": whale})
    saviour.deposit(encode_single('bytes32', b'ETH-A'), safe_id, rai.balanceOf(whale)/3, {"from": whale}) 
    fRai.mint(0, {"from": whale})
    crRai.mint(0, {"from": whale})
    strategy.harvest()
    print("After harvest 2 ... ")

    status = strategy.lendStatuses()
    form = "{:.2%}"
    formS = "{:,.0f}"
    for j in status:
        print(
            f"Lender: {j[0]}, Deposits: {formS.format(j[1]/1e18)}, APR: {form.format(j[2]/1e18)}"
        )
    saviour.deposit(encode_single('bytes32', b'ETH-A'), safe_id, rai.balanceOf(whale)/3, {"from": whale})
    saviour.deposit(encode_single('bytes32', b'ETH-A'), safe_id, rai.balanceOf(strategist), {"from": strategist}) 

    fRai.mint(0, {"from": whale})
    strategy.harvest()

    print("After harvest 3 ... ")

    status = strategy.lendStatuses()
    form = "{:.2%}"
    formS = "{:,.0f}"
    for j in status:
        print(
            f"Lender: {j[0]}, Deposits: {formS.format(j[1]/1e18)}, APR: {form.format(j[2]/1e18)}"
        )
    assert strategy.harvestTrigger(1000) == True

    strategy.harvest()

    # strategist withdraws
    shareprice = vault.pricePerShare()

    shares = vault.balanceOf(strategist)
    expectedout = shares * (shareprice / 1e18) * (10 ** (decimals * 2))
    balanceBefore = currency.balanceOf(strategist)

    # genericStateOfStrat(strategy, currency, vault)
    # genericStateOfVault(vault, currency)
    status = strategy.lendStatuses()
    form = "{:.2%}"
    formS = "{:,.0f}"
    for j in status:
        print(
            f"Lender: {j[0]}, Deposits: {formS.format(j[1]/1e18)}, APR: {form.format(j[2]/1e18)}"
        )

    
    # Whale withdraws some
    saviour.withdraw(encode_single('bytes32', b'ETH-A'), safe_id, vault.balanceOf(saviour)/2, whale, {"from": whale}) 

    vault.withdraw(vault.balanceOf(strategist), {"from": strategist})
    balanceAfter = currency.balanceOf(strategist)

    # genericStateOfStrat(strategy, currency, vault)
    # genericStateOfVault(vault, currency)
    status = strategy.lendStatuses()

    chain.mine(waitBlock)
    withdrawn = balanceAfter - balanceBefore
    assert withdrawn > expectedout * 0.99 and withdrawn < expectedout * 1.01

    profit = balanceAfter - starting_balance
    assert profit > 0
    print(profit)