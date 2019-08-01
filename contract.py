from ontology.interop.System.App import DynamicAppCall
from ontology.interop.System.Blockchain import GetHeight
from ontology.interop.System.ExecutionEngine import GetExecutingScriptHash
from ontology.interop.System.Runtime import Log, CheckWitness, Serialize
from ontology.interop.System.Storage import GetContext, Get, Put, Delete
ctx = GetContext()
selfContractAddr = GetExecutingScriptHash()

ONTLOCK_ENTRY = 'ONTLOCK-ENTRY-KEY'
STAKE_PREFIX = 'LOCK-STAKE-KEY'
UNSTAKE_PREFIX = 'LOCK-UNSTAKE-KEY'
STORED_KEY = 'STORED-KEY'
STAKE_DELAY = 45000
STAKE_PRICE = 50
LOCK_HASH = 'ebe0ff4ee0524c2dabcd1331c3c842896bf40b97'


def Main(operation, args):
    if operation == 'put':
        Require(len(args) == 4)
        address = args[0]
        website = args[1]
        username = args[2]
        password = args[3]
        return put(address, website, username, password)
    elif operation == 'get':
        Require(len(args) == 2)
        address = args[0]
        website = args[1]
        return get(address, website)
    elif operation == 'delete':
        Require(len(args) == 2)
        address = args[0]
        website = args[1]
        return delete(address, website)
    elif operation == 'stake':
        Require(len(args) == 2)
        address = args[0]
        amount = args[1]
        return stake(address, amount)
    elif operation == 'unstake':
        Require(len(args) == 2)
        address = args[0]
        amount = args[1]
        return unstake(address, amount)
    elif operation == 'getCurrentStake':
        Require(len(args) == 1)
        address = args[0]
        return getCurrentStake(address)
    elif operation == 'getLOCKStaked':
        Require(len(args) == 1)
        address = args[0]
        return getLOCKStaked(address)
    return False


def put(address, website, username, password):
    RequireIsAddress(address)
    RequireWitness(address)
    RequireShorterThan(website, 65)
    RequireShorterThan(username, 65)
    RequireShorterThan(password, 65)
    return do_put(address, website, username, password)


def get(address, website):
    RequireIsAddress(address)
    RequireShorterThan(website, 65)
    return do_get(address, website)


def delete(address, website):
    RequireIsAddress(address)
    RequireWitness(address)
    RequireShorterThan(website, 65)
    return do_delete(address, website)


def do_put(address, website, username, password):
    storageKey = get_pass_key(address, website)
    currentData = Get(ctx, storageKey)
    stored = get_stored_count(address)
    if currentData is None:
        stored += 1
    allowance = get_allowance(address)

    Require(stored <= allowance)
    set_stored_count(address, stored)
    entry = {"username": username, "password": password}
    Put(ctx, storageKey, Serialize(entry))
    return True


def do_get(address, website):
    storageKey = get_pass_key(address, website)
    storage = Get(ctx, storageKey)
    if storage is not None:
        return storage
    return ""


def do_delete(address, website):
    storageKey = get_pass_key(address, website)
    currentData = Get(ctx, storageKey)
    if currentData is None:
        return True

    stored = get_stored_count(address)
    set_stored_count(address, stored - 1)
    Delete(ctx, storageKey)
    return True


def stake(address, amount):
    key = get_stake_key(address)
    current = Get(ctx, key)
    to_transfer = get_stake_size(amount)
    Require(DynamicAppCall(LOCK_HASH, 'transfer', [address, selfContractAddr, to_transfer]))
    Put(ctx, key, current + amount)
    currentHeight = GetHeight()
    set_unstake_height(address, currentHeight + STAKE_DELAY)
    return True


def unstake(address, amount):
    currentHeight = GetHeight()
    unstakeHeight = get_unstake_height(address)
    Require(currentHeight >= unstakeHeight)
    key = get_stake_key(address)
    current = Get(ctx, key)
    Require(current >= amount)
    to_transfer = get_stake_size(amount)
    Require(DynamicAppCall(LOCK_HASH, 'transfer', [selfContractAddr, address, to_transfer]))
    if current == amount:
        Delete(ctx, key)
    else:
        Put(ctx, key, current - amount)
    return True


def getCurrentStake(address):
    return get_stake(address)


def getLOCKStaked(address):
    amount = get_stake(address)
    return get_stake_size(amount)

# Helpers

def get_stake_size(amount):
    factor = 100000000 # 10^8
    return amount * factor * STAKE_PRICE


def get_unstake_height(address):
    key = get_unstake_key(address)
    return Get(ctx, key)


def set_unstake_height(address, height):
    key = get_unstake_key(address)
    Put(ctx, key, height)


def get_stored_count(address):
    key = concat(STORED_KEY, address) # pylint: disable=E0602
    return Get(ctx, key)


def set_stored_count(address, count):
    key = concat(STORED_KEY, address) # pylint: disable=E0602
    Put(ctx, key, count)


def get_allowance(address):
    currentStake = get_stake(address)
    base = 5
    allowance = base + currentStake * 5
    return allowance


def get_stake(address):
    key = get_stake_key(address)
    return Get(ctx, key)


def get_stake_key(address):
    key = concat(STAKE_PREFIX, address) # pylint: disable=E0602
    return key


def get_unstake_key(address):
    key = concat(UNSTAKE_PREFIX, address) # pylint: disable=E0602
    return key


def get_pass_key(address, website):
    '''
    Creates a unique storage key for the given address and website.

    :param address: The user's address.
    :param website: The website to store information for.
    '''
    return concat(concat(ONTLOCK_ENTRY, address), website) # pylint: disable=E0602


def RequireShorterThan(string, length):
    '''
    Raises an exception if the string's length exceeds the limit.

    :param string: The string to check.
    :param length: The length limit.
    '''
    Require(len(string) < length, "String is too long")


def RequireIsAddress(address):
    '''
    Raises an exception if the given address is not the correct length.

    :param address: The address to check.
    '''
    Require(len(address) == 20, "Address has invalid length")


def RequireWitness(address):
    '''
    Raises an exception if the given address is not a witness.

    :param address: The address to check.
    '''
    Require(CheckWitness(address), "Address is not witness")


def Require(expr, message="There was an error"):
    '''
    Raises an exception if the given expression is false.

    :param expr: The expression to evaluate.
    :param message: The error message to log.
    '''
    if not expr:
        Log(message)
        raise Exception(message)
