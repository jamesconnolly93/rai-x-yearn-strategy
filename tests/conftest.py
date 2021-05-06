import pytest
from brownie import config, Wei, Contract


# specific addresses
@pytest.fixture
def rai(interface):
    yield interface.ERC20("0x03ab458634910AaD20eF5f1C8ee96F1D6ac54919")


# change these fixtures for generic tests
@pytest.fixture
def currency(rai):
    yield rai


@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass


@pytest.fixture
def whale(accounts, web3, weth, rai):
    #rai
    acc = accounts.at("0x635B230C3fdf6A466bb6dc3b9B51a8cEB0659b67", force=True)
    acc2 = accounts.at("0x4a0Ea6ad985F6526de7d1adE562e1007E9c5d757", force=True) # A full uniswap pool of RAI :)
    rai.transfer(acc, rai.balanceOf(acc2), {"from": acc2})
    # lots of weth account
    wethAcc = accounts.at("0x0092081D8E3E570E9E88F4563444bd4B92684502", force=True)
    weth.approve(acc, 2 ** 256 - 1, {"from": wethAcc})
    weth.transfer(acc, weth.balanceOf(wethAcc), {"from": wethAcc})

    assert weth.balanceOf(acc) > 0
    yield acc


@pytest.fixture()
def strategist(accounts, whale, currency):
    decimals = currency.decimals()
    strategist = accounts[1]
    currency.transfer(strategist, 20_000 * (10 ** decimals), {"from": whale})
    yield strategist


@pytest.fixture
def samdev(accounts):
    yield accounts.at("0xC3D6880fD95E06C816cB030fAc45b3ffe3651Cb0", force=True)


@pytest.fixture
def gov(accounts):
    yield accounts[3]


@pytest.fixture
def rewards(gov):
    yield gov  # TODO: Add rewards contract


@pytest.fixture
def guardian(accounts):
    # YFI Whale, probably
    yield accounts[2]


@pytest.fixture
def keeper(accounts):
    # This is our trusty bot!
    yield accounts[4]


@pytest.fixture
def rando(accounts):
    yield accounts[9]


@pytest.fixture
def weth(interface):
    yield interface.IWETH("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2")



@pytest.fixture
def crRai(interface):
    yield interface.CErc20I("0xf8445C529D363cE114148662387eba5E62016e20")


@pytest.fixture
def fRai(interface): #fRAI-9
    yield interface.CErc20I("0x752F119bD4Ee2342CE35E2351648d21962c7CAfE")


@pytest.fixture(scope="module", autouse=True)
def shared_setup(module_isolation):
    pass


@pytest.fixture
def vault(gov, rewards, guardian, currency, pm):
    Vault = pm(config["dependencies"][0]).Vault
    vault = Vault.deploy({"from": guardian})
    vault.initialize(currency, gov, rewards, "", "")
    vault.setManagementFee(0, {"from": gov})
    yield vault


@pytest.fixture
def strategy(
    strategist,
    gov,
    rewards,
    keeper,
    vault,
    crRai,
    fRai,
    Strategy,
    GenericCream,
    GenericFuse
):
    strategy = strategist.deploy(Strategy, vault)
    strategy.setKeeper(keeper, {"from": gov})
    strategy.setWithdrawalThreshold(0, {"from": gov})
    strategy.setRewards(rewards, {"from": strategist})

    fusePlugin = strategist.deploy(GenericFuse, strategy, "Fuse", fRai)
    creamPlugin = strategist.deploy(GenericCream, strategy, "Cream", crRai)

    strategy.addLender(fusePlugin, {"from": gov})
    strategy.addLender(creamPlugin, {"from": gov})
    assert strategy.numLenders() == 2

    yield strategy


@pytest.fixture
def coin_join():
    yield Contract("0x0A5653CCa4DB1B6E265F47CAf6969e64f1CFdC45")

@pytest.fixture
def liquidation_engine():
    yield Contract("0x27Efc6FFE79692E0521E7e27657cF228240A06c2")

@pytest.fixture
def oracle_relayer():
    yield Contract("0x4ed9C0dCa0479bC64d8f4EB3007126D5791f7851")

@pytest.fixture
def safe_manager():
    yield Contract("0xEfe0B4cA532769a3AE758fD82E1426a03A94F185")

@pytest.fixture
def saviour_registry():
    yield Contract("0x2C6F6784585B45906Fce24f30C99f8ad6d94b5d4")

@pytest.fixture
def system_coin_oracle():
    yield Contract("0x12A5E1c81B10B264A575930aEae80681DDF595fe")

@pytest.fixture
def c_ratio_setter():
    yield Contract("0xD58e867E1548D8294bc6C77585AF4015ab457880")

@pytest.fixture
def saviour(
    YearnCoinSafeSaviour,
    coin_join,
    c_ratio_setter,
    system_coin_oracle,
    liquidation_engine,
    oracle_relayer,
    safe_manager,
    saviour_registry,
    vault,
    strategist
):
    yield strategist.deploy(
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