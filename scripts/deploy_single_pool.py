import os
import sys
from dataclasses import dataclass
from typing import List

import boa
from boa.network import NetworkEnv
from eth_account import Account
from eth_typing import Address
from rich.console import Console as RichConsole

from eth_utils import function_signature_to_4byte_selector


logger = RichConsole(file=sys.stdout)
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

DEPLOYER_ADDRESS = os.getenv('DEPLOYER_ADDRESS')
DEPLOYER_PKEY = os.getenv('DEPLOYER_PKEY')
RPC_ETHEREUM = os.getenv('RPC_ETHEREUM')


deployments = {
    # Ethereum
    "ethereum:sepolia": {"factory": "0xfb37b8D939FFa77114005e61CFc2e543d6F49A81",},
    "ethereum:mainnet": {"factory": "0x6A8cbed756804B16E05E741eDaBd5cB544AE21bf",},
    # Layer 2
    "arbitrum:mainnet": {"factory": "0x9AF14D26075f142eb3F292D5065EB3faa646167b",},
    "optimism:mainnet": {"factory": "0x5eeE3091f747E60a045a2E715a4c71e600e31F6E",},
    "base:mainnet": {"factory": "0xd2002373543Ce3527023C75e7518C274A51ce712",},
    "linea:mainnet": {"factory": "0x5eeE3091f747E60a045a2E715a4c71e600e31F6E",},
    "scroll:mainnet": {"factory": "0x5eeE3091f747E60a045a2E715a4c71e600e31F6E",},
    "zksync:mainnet": {"factory": "",},
    "pzkevm:mainnet": {"factory": "0xd2002373543Ce3527023C75e7518C274A51ce712",},
    "mantle:mainnet": {"factory": ""},
    # Layer 1
    "gnosis:mainnet": {"factory": "0xbC0797015fcFc47d9C1856639CaE50D0e69FbEE8",},
    "polygon:mainnet": {"factory": "0x1764ee18e8B3ccA4787249Ceb249356192594585",},
    "avax:mainnet": {"factory": "0x1764ee18e8B3ccA4787249Ceb249356192594585",},
    "ftm:mainnet": {"factory": "0xe61Fb97Ef6eBFBa12B36Ffd7be785c1F5A2DE66b",},
    "bsc:mainnet": {"factory": "0xd7E72f3615aa65b92A4DBdC211E296a35512988B",},
    "celo:mainnet": {"factory": "0x1764ee18e8B3ccA4787249Ceb249356192594585",},
    "kava:mainnet": {"factory": "0x1764ee18e8B3ccA4787249Ceb249356192594585",},
    "aurora:mainnet": {"factory": "0x5eeE3091f747E60a045a2E715a4c71e600e31F6E",},
    "tron:mainnet": {"factory": "",},
}


# -------------------------- POOL SETUP --------------------------


@dataclass
class PoolSettings:
    name: str
    symbol: str
    coins: List[Address]
    A: int
    fee: int
    offpeg_fee_multiplier: int
    ma_exp_time: int
    implementation_idx: int
    asset_types: List[int]
    method_ids: List[int]
    oracles: List[Address]


pool_settings = {
    "ethereum:mainnet": {
        "plain": [
            "osETH/rETH",  # name
            "oseth-reth",  # symbol
            [
                "0xf1C9acDc66974dFB6dEcB12aA385b9cD01190E38",  # osETH
                "0xae78736Cd615f374D3085123A210448E74Fc6393",  # rETH
            ],
            500,  # A
            1000000,  # fee
            20000000000,  # offpeg_fee_multiplier
            865,  # ma_exp_time
            0,  # implementation index
            [1, 1],  # asset_types
            [b"\x67\x9a\xef\xce", b"\xe6\xaa\x21\x6c"],  # method_ids
            ["0x8023518b2192FB5384DAdc596765B3dD1cdFe471", "0xae78736Cd615f374D3085123A210448E74Fc6393"],  # oracles
        ],
    }
}



'''
rETH
0xae78736Cd615f374D3085123A210448E74Fc6393 
https://etherscan.io/address/0xae78736Cd615f374D3085123A210448E74Fc6393#readContract
Rate function: getExchangeRate() on token, method_id:  0xe6aa216c
method_id = function_signature_to_4byte_selector('getExchangeRate()')


osETH
0xf1C9acDc66974dFB6dEcB12aA385b9cD01190E38 
https://etherscan.io/address/0xf1C9acDc66974dFB6dEcB12aA385b9cD01190E38#readContract

Rate for osETH
0x8023518b2192FB5384DAdc596765B3dD1cdFe471
https://etherscan.io/address/0x8023518b2192FB5384DAdc596765B3dD1cdFe471#readContract

Rate function: getRate() on token, method_id:  0x679aefce, \x67\x9a\xef\xce

'''



def deploy_pool(network, url, account, pool_type, fork):
    
    logger.log(f"Deploying pool on {network} ...")

    method_id = function_signature_to_4byte_selector('getRate()')
    print(method_id)
    if fork:
        boa.env.fork(url)
        logger.log("Forkmode ...")
        boa.env.eoa = DEPLOYER_ADDRESS
        # boa.env.eoa =  ""  # set eoa address here
    else:
        logger.log("Prodmode ...")
        boa.set_env(NetworkEnv(url))
        boa.env.add_account(Account.from_key(account))

    factory = boa.load_partial("./contracts/main/CurveStableSwapFactoryNG.vy")
    factory = factory.at(deployments["ethereum:mainnet"]["factory"])

    logger.log("Deploying pool ...")
    args = pool_settings[network][pool_type]
    if pool_type == "plain":
        logger.log(*args)
        amm_address = factory.deploy_plain_pool(*args)
    elif pool_type == "meta":
        amm_address = factory.deploy_metapool(*args)

    logger.log(f"Deployed Plain pool {amm_address}.")

    pool = boa.load_partial("./contracts/main/CurveStableSwapNG.vy")
    pool = pool.at(amm_address)
    # test some stuff

    initial_A = pool.initial_A()
    logger.log(f"pool.initial_A() {initial_A}.")

    fee = pool.fee()
    logger.log(f"pool.fee() {fee}.")

    #dynamic_fee = pool.dynamic_fee(0,1)
    #logger.log(f"pool.dynamic_fee() {dynamic_fee}.")

    admin_fee = pool.admin_fee()
    logger.log(f"pool.admin_fee() {admin_fee}.")

    stored_rates = pool.stored_rates()
    logger.log(f"pool.stored_rates() {stored_rates}.")

    price_oracle = pool.price_oracle(0)
    logger.log(f"pool.price_oracle(0) {price_oracle}.")

    price_oracle = pool.price_oracle(0)
    logger.log(f"pool.price_oracle(0) {price_oracle}.")


def main():
    fork=True
    deploy_pool(
        "ethereum:mainnet", 
        RPC_ETHEREUM,
        DEPLOYER_PKEY, 
        "plain",
        fork
    )


if __name__ == "__main__":
    main()
