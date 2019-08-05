from ontology.interop.System.App import DynamicAppCall
from ontology.interop.System.Blockchain import GetHeight
from ontology.interop.System.ExecutionEngine import GetExecutingScriptHash
from ontology.interop.System.Runtime import Log, CheckWitness, Serialize, Deserialize
from ontology.interop.System.Storage import GetContext, Get, Put, Delete
ctx = GetContext()
selfContractAddr = GetExecutingScriptHash()

ONTLOCK_ENTRY = '\x01'
STAKE_PREFIX = '\x02'
UNSTAKE_PREFIX = '\x03'
BUY_PREFIX = '\x04'
BURNED_PREFIX = '\x05'
STORED_KEY = '\x06'

STAKE_DELAY = 45000
STAKE_PRICE = 50
BUY_PRICE = 500
LOCK_HASH = 'ebe0ff4ee0524c2dabcd1331c3c842896bf40b97'

base = 5
multiplier = 5
size_limit = 33

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
    elif operation == 'getAll':
        Require(len(args) == 1)
        address = args[0]
        return getAll(address)
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
    elif operation == 'getAllowance':
        Require(len(args) == 1)
        address = args[0]
        return getAllowance(address)
    elif operation == 'buy':
        Require(len(args) == 2)
        address = args[0]
        amount = args[1]
        return buy(address, amount)
    elif operation == 'getBurned':
        Require(len(args) == 0)
        return getBurned()
    return False


def put(address, website, username, password):
    RequireIsAddress(address)
    RequireWitness(address)
    RequireShorterThan(website, size_limit)
    RequireShorterThan(username, size_limit)
    RequireShorterThan(password, size_limit)
    return do_put(address, website, username, password)


def get(address, website):
    RequireIsAddress(address)
    RequireShorterThan(website, size_limit)
    return do_get(address, website)


def getAll(address):
    RequireIsAddress(address)
    key = concat(ONTLOCK_ENTRY, address) # pylint: disable=E0602
    data = Get(ctx, key)
    return data


def delete(address, website):
    RequireIsAddress(address)
    RequireWitness(address)
    RequireShorterThan(website, size_limit)
    return do_delete(address, website)


def do_put(address, website, username, password):
    user_dict = get_global_dict(address)
    storageKey = get_storage_key(address, website)
    isStored = Get(ctx, storageKey)
    storedCount = get_stored_count(address)
    if isStored is False:
        storedCount += 1
    allowance = get_allowance(address)

    Require(storedCount <= allowance)
    set_stored_count(address, storedCount)

    entry = {'username': username, 'password': password}
    user_dict[website] = entry
    set_global_dict(address, user_dict)

    Put(ctx, storageKey, True)
    return True


def do_get(address, website):
    user_dict = get_global_dict(address)
    storageKey = get_storage_key(address, website)
    isStored = Get(ctx, storageKey)
    if isStored:
        entry = user_dict[website]
        return Serialize(entry)
    return ''


def do_delete(address, website):
    storageKey = get_storage_key(address, website)
    isStored = Get(ctx, storageKey)
    if isStored is False:
        return False

    user_dict = get_global_dict(address)
    user_dict.remove(website)
    set_global_dict(address, user_dict)

    storedCount = get_stored_count(address)
    set_stored_count(address, storedCount - 1)
    Delete(ctx, storageKey)
    return True


def stake(address, amount):
    RequireIsAddress(address)
    RequireWitness(address)

    key = get_stake_key(address)
    current = Get(ctx, key)
    to_transfer = get_stake_size(amount)
    Require(DynamicAppCall(LOCK_HASH, 'transfer', [address, selfContractAddr, to_transfer]))
    Put(ctx, key, current + amount)
    currentHeight = GetHeight()
    set_unstake_height(address, currentHeight + STAKE_DELAY)
    return True


def unstake(address, amount):
    RequireIsAddress(address)
    RequireWitness(address)

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
    RequireIsAddress(address)
    return get_stake(address)


def getLOCKStaked(address):
    RequireIsAddress(address)
    amount = get_stake(address)
    return get_stake_size(amount)


def getAllowance(address):
    RequireIsAddress(address)
    return get_allowance(address)


def buy(address, amount):
    RequireIsAddress(address)
    RequireWitness(address)

    key = get_buy_key(address)
    current = Get(ctx, key)
    to_transfer = get_buy_size(amount)
    Require(DynamicAppCall(LOCK_HASH, 'transfer', [address, selfContractAddr, to_transfer]))
    Put(ctx, key, current + amount)
    burn(to_transfer)
    return True


def getBurned():
    key = get_burned_key()
    return Get(ctx, key)

# Global Dict Storage

def get_global_dict(address):
    key = concat(ONTLOCK_ENTRY, address) # pylint: disable=E0602
    data = Get(ctx, key)
    if data is None:
        return {}
    return Deserialize(data)


def set_global_dict(address, dct):
    key = concat(ONTLOCK_ENTRY, address) # pylint: disable=E0602
    Put(ctx, key, Serialize(dct))

# Helpers

def burn(amount):
    burnedKey = get_burned_key()
    burned = Get(ctx, burnedKey)
    Put(ctx, burnedKey, burned + amount)


def get_buy_size(amount):
    factor = 100000000 # 10^8
    return amount * factor * BUY_PRICE


def get_bought(address):
    key = get_buy_key(address)
    return Get(ctx, key)


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
    currentBought = get_bought(address)
    allowance = base + currentStake * multiplier + currentBought * multiplier
    return allowance


def get_stake(address):
    key = get_stake_key(address)
    return Get(ctx, key)

# Keys

def get_stake_key(address):
    key = concat(STAKE_PREFIX, address) # pylint: disable=E0602
    return key


def get_unstake_key(address):
    key = concat(UNSTAKE_PREFIX, address) # pylint: disable=E0602
    return key


def get_buy_key(address):
    key = concat(BUY_PREFIX, address) # pylint: disable=E0602
    return key


def get_burned_key():
    return concat(BURNED_PREFIX) # pylint: disable=E0602


def get_storage_key(address, website):
    return concat(address, website) # pylint: disable=E0602

# Require

def RequireShorterThan(string, length):
    Require(len(string) < length, 'String is too long')


def RequireIsAddress(address):
    Require(len(address) == 20, 'Address has invalid length')


def RequireWitness(address):
    Require(CheckWitness(address), 'Address is not witness')


def Require(expr, message='There was an error'):
    if not expr:
        Log(message)
        raise Exception(message)
