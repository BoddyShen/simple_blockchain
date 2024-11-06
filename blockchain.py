"""
In this assignment you will extend and implement a class framework to create a simple but functional blockchain that combines the ideas of proof-of-work, transactions, blocks, and blockchains.
You may create new member functions, but DO NOT MODIFY any existing APIs.  These are the interface into your blockchain.


This blockchain has the following consensus rules (it is a little different from Bitcoin to make testing easier):

Blockchain

1. There are no consensus rules pertaining to the minimum proof-of-work of any blocks.  That is it has no "difficulty adjustment algorithm".
Instead, your code will be expected to properly place blocks of different difficulty into the correct place in the blockchain and discover the most-work tip.

2. A block with no transactions (no coinbase) is valid (this will help us isolate tests).

3. If a block as > 0 transactions, the first transaction MUST be the coinbase transaction.

Block Merkle Tree

1. You must use sha256 hash 
2. You must use 0 if additional items are needed to pad odd merkle levels
(more specific information is included below)

Transactions

1. A transaction with inputs==None is a valid mint (coinbase) transaction.  The coins created must not exceed the per-block "minting" maximum.

2. If the transaction is not a coinbase transaction, coins cannot be created.  In other words, coins spent (inputs) must be >= coins sent (outputs).

3. Constraint scripts (permission to spend) are implemented via python lambda expressions (anonymous functions).  These constraint scripts must accept a list of parameters, and return True if
   permission to spend is granted.  If execution of the constraint script throws an exception or returns anything except True do not allow spending!

461: You may assume that every submitted transaction is correct.
     This means that you should just make the Transaction validate() function return True
     You do not need to worry about tracking the UTXO (unspent transaction outputs) set.

661: You need to verify transactions, their constraint and satisfier scripts, and track the UTXO set.


Some useful library functions:

Read about hashlib.sha256() to do sha256 hashing in python.
Convert the sha256 array of bytes to a big endian integer via: int.from_bytes(bunchOfBytes,"big")

Read about the "dill" library to serialize objects automatically (dill.dumps()).  "Dill" is like "pickle", but it can serialize python lambda functions, which you need to install via "pip3 install dill".  The autograder has this library pre-installed.
You'll probably need this when calculating a transaction id.

"""
import sys
assert sys.version_info >= (3, 6)
import hashlib
import pdb
import copy
import json
# pip3 install dill
import dill as serializer

class Output:
    """ This models a transaction output """
    def __init__(self, constraint = None, amount = 0):
        """ constraint is a function that takes 1 argument which is a list of 
            objects and returns True if the output can be spent.  For example:
            Allow spending without any constraints (the "satisfier" in the Input object can be anything)
            lambda x: True

            Allow spending if the spender can add to 100 (example: satisfier = [40,60]):
            lambda x: x[0] + x[1] == 100

            If the constraint function throws an exception, do not allow spending.
            For example, if the satisfier = ["a","b"] was passed to the previous constraint script

            If the constraint is None, then allow spending without constraint

            amount is the quantity of tokens associated with this output """
        
        self.constraint = constraint or (lambda x: True)  # No constraint if none provided
        self.amount = amount

class Input:
    """ This models an input (what is being spent) to a blockchain transaction """
    def __init__(self, txHash, txIdx, satisfier):
        """ This input references a prior output by txHash and txIdx.
            txHash is therefore the prior transaction hash
            txIdx identifies which output in that prior transaction is being spent.  It is a 0-based index.
            satisfier is a list of objects that is be passed to the Output constraint script to prove that the output is spendable.
        """
        self.txHash = txHash
        self.txIdx = txIdx
        self.satisfier = satisfier

class Transaction:
    """ This is a blockchain transaction """
    def __init__(self, inputs=None, outputs=None, data = None):
        """ Initialize a transaction from the provided parameters.
            inputs is a list of Input objects that refer to unspent outputs.
            outputs is a list of Output objects.
            data is a byte array to let the transaction creator put some 
              arbitrary info in their transaction.
        """
        self.inputs = inputs
        self.outputs = outputs
        self.data = data

    def getHash(self):
        """Return this transaction's probabilistically unique identifier as a big-endian integer"""
        serialized = serializer.dumps(self)
        return int.from_bytes(hashlib.sha256(serialized).digest(), 'big')

    def getInputs(self):
        """ return a list of all inputs that are being spent """
        return self.inputs

    def getOutput(self, n):
        """ Return the output at a particular index """
        return self.outputs[n] if n < len(self.outputs) else None

    def validateMint(self, maxCoinsToCreate):
        """ Validate a mint (coin creation) transaction.
            A coin creation transaction should have no inputs,
            and the sum of the coins it creates must be less than maxCoinsToCreate.
        """
        if self.inputs:
            return False
        return sum(output.amount for output in self.outputs) <= maxCoinsToCreate

    def validate(self, unspentOutputDict):
        """ Validate this transaction given a dictionary of unspent transaction outputs.
            unspentOutputDict is a dictionary of items of the following format: { (txHash, offset) : Output }
        """
        # if you are taking 461: return True
        # return True
        total_input = sum(unspentOutputDict[(input.txHash, input.txIdx)].amount for input in self.inputs)
        total_output = sum(output.amount for output in self.outputs)

        if total_input < total_output:
            return False
        for input in self.inputs:
            if not unspentOutputDict[(input.txHash, input.txIdx)].constraint(input.satisfier):
                return False
        return True


class HashableMerkleTree:
    """ A merkle tree of hashable objects.

        If no transaction or leaf exists, use 32 bytes of 0.
        The list of objects that are passed must have a member function named
        .getHash() that returns the object's sha256 hash as an big endian integer.

        Your merkle tree must use sha256 as your hash algorithm and big endian
        conversion to integers so that the tree root is the same for everybody.
        This will make it easy to test.

        If a level has an odd number of elements, append a 0 value element.
        if the merkle tree has no elements, return 0.

    """

    def __init__(self, hashableList = None):
        self.hashableList = hashableList or []

    def calcMerkleRoot(self):
        """ Calculate the merkle root of this tree."""
        if not self.hashableList:
            return 0
        
        if len(self.hashableList) == 1:
            return self.hashableList[0].getHash()
        
        nodes = [int.to_bytes(h.getHash(), 32, 'big') for h in self.hashableList]

        while len(nodes) > 1:
            if len(nodes) % 2 == 1:
                nodes.append(bytes(32))  # append 32 bytes of 0 if odd number of nodes
            nodes = [hashlib.sha256(nodes[i] + nodes[i + 1]).digest() for i in range(0, len(nodes), 2)]
        return int.from_bytes(nodes[0], 'big')

class BlockContents:
    """ The contents of the block (merkle tree of transactions)
        This class isn't really needed.  I added it so the project could be cut into
        just the blockchain logic, and the blockchain + transaction logic.
    """
    def __init__(self):
        self.data = HashableMerkleTree()
        self.transactions = []

    def setData(self, d):
        # Ensure that data is a HashableMerkleTree
        if isinstance(d, list):
            self.transactions = d
            self.data = HashableMerkleTree(d)

        elif isinstance(d, HashableMerkleTree):
            self.data = d
        else:
            raise TypeError("Data must be a list of hashable objects or a HashableMerkleTree.")

    def getData(self):
        return self.data

    def calcMerkleRoot(self):
        return self.data.calcMerkleRoot()

class Block:
    """ This class should represent a blockchain block.
        It should have the normal fields needed in a block and also an instance of "BlockContents"
        where we will store a merkle tree of transactions.
    """
    def __init__(self):
        # Hint, beyond the normal block header fields what extra data can you keep track of per block to make implementing other APIs easier?
        self.contents = BlockContents()
        self.priorHash = 0
        self.target = 0
        self.nonce = 0
        self.transactions = self.contents.transactions

    def getContents(self):
        """ Return the Block content (a BlockContents object)"""
        return self.contents

    def setContents(self, data):
        """ set the contents of this block's merkle tree to the list of objects in the data parameter """
        self.contents.setData(data)

    def setTarget(self, target):
        """ Set the difficulty target of this block """
        self.target = target

    def getTarget(self):
        """ Return the difficulty target of this block """
        return self.target

    def getHash(self):
        """ Calculate the hash of this block. Return as an integer """
        serialized = serializer.dumps((self.priorHash, self.contents.calcMerkleRoot(), self.nonce))
        return int.from_bytes(hashlib.sha256(serialized).digest(), 'big')

    def setPriorBlockHash(self, priorHash):
        """ Assign the parent block hash """
        self.priorHash = priorHash

    def getPriorBlockHash(self):
        """ Return the parent block hash """
        return self.priorHash

    def mine(self, tgt):
        """Update the block header to the passed target (tgt) and then search for a nonce which produces a block who's hash is less than the passed target, "solving" the block"""
        self.target = tgt
        while self.getHash() >= self.target:
            self.nonce += 1

    def validate(self, unspentOutputs, maxMint):
        """ Given a dictionary of unspent outputs, and the maximum amount of
            coins that this block can create, determine whether this block is valid.
            Valid blocks satisfy the POW puzzle, have a valid coinbase tx, and have valid transactions (if any exist).

            Return None if the block is invalid.

            Return a new UTXO set if the block is valid.
        """
        assert isinstance(unspentOutputs, dict), "unspentOutputs must be a dictionary of tuples (hash, index) -> Output"

        # Step 1: Check Proof of Work
        if self.getHash() >= self.target:
            return None  # Block does not meet the PoW requirement

        # Step 2: Initialize a new UTXO set to track changes in this block's transactions
        new_utxo = unspentOutputs.copy()

        # Step 3: Validate the coinbase transaction
        if self.transactions:
            coinbase = self.transactions[0]
            if not coinbase.validateMint(maxMint):
                return None  # Coinbase transaction exceeds the minting limit

            # Step 4: Validate non-coinbase transactions
            for tx in self.transactions[1:]:
                if not tx.validate(new_utxo):
                    return None  # Invalid transaction detected

                # Step 5: Update the UTXO set for each valid transaction
                # Add transaction outputs to the UTXO set
                for idx, output in enumerate(tx.outputs):
                    new_utxo[(tx.getHash(), idx)] = output

                # Remove inputs from the UTXO set as they are now spent
                for input in tx.inputs:
                    if (input.txHash, input.txIdx) in new_utxo:
                        del new_utxo[(input.txHash, input.txIdx)]
                    else:
                        return None  # Input does not exist in UTXO set (double-spending or invalid reference)

        # Step 6: Return the updated UTXO set if block is valid
        return new_utxo

class Blockchain(object):

    def __init__(self, genesisTarget, maxMintCoinsPerTx):
        """ Initialize a new blockchain and create a genesis block.
            genesisTarget is the difficulty target of the genesis block (that you should create as part of this initialization).
            maxMintCoinsPerTx is a consensus parameter -- don't let any block into the chain that creates more coins than this!
        """
        self.genesisTarget = genesisTarget
        self.maxMintCoinsPerTx = maxMintCoinsPerTx
        # self.blocks = []
        self.blocks = {} # {block hash: block}

        self.cumulative_work = {}
        self.utxo_state = {}
        
        genesis = Block()
        genesis.setTarget(genesisTarget)
        genesis.mine(genesisTarget)
        # self.blocks.append(genesis)
        self.blocks[genesis.getHash()] = genesis

        self.cumulative_work[genesis.getHash()] = self.getWork(genesisTarget)

    def getTip(self):
        """ Return the block at the tip (end) of the blockchain fork that has the largest amount of work"""
        max_work = max(self.cumulative_work, key=self.cumulative_work.get)
        for block_hash in self.blocks:
            if block_hash == max_work:
                return self.blocks[block_hash]

    def getWork(self, target):
        """Get the "work" needed for this target.  Work is the ratio of the genesis target to the passed target"""
        return self.genesisTarget / target

    def getCumulativeWork(self, blkHash):
        """Return the cumulative work for the block identified by the passed hash.  Return None if the block is not in the blockchain"""
        return self.cumulative_work.get(blkHash, None)

    def getBlocksAtHeight(self, height):
        """Return an array of all blocks in the blockchain at the passed height (including all forks)"""
        
        results = []
        for block_hash in self.blocks:
            curr_block = self.blocks[block_hash]
            curr_height = 0
            
            while curr_block.priorHash in self.blocks:
                curr_height += 1
                curr_block = self.blocks[curr_block.priorHash]

            if curr_height == height:
                results.append(self.blocks[block_hash])
        return results

    def extend(self, block):
        """Adds this block into the blockchain in the proper location, if it is valid.  The "proper location" may not be the tip!

           Hint: Note that this means that you must validate transactions for a block that forks off of any position in the blockchain.
           The easiest way to do this is to remember the UTXO set state for every block, not just the tip.
           For space efficiency "real" blockchains only retain a single UTXO state (the tip).  This means that during a blockchain reorganization
           they must travel backwards up the fork to the common block, "undoing" all transaction state changes to the UTXO, and then back down
           the new fork.  For this assignment, don't implement this detail, just retain the UTXO state for every block
           so you can easily "hop" between tips.

           Return false if the block is invalid (breaks any miner constraints), and do not add it to the blockchain."""
        
        # find the prior block
        print("block.priorHash", block.priorHash)
        print("block.transactions", block.transactions)

        prior_block = self.blocks.get(block.priorHash, None)
        if prior_block is None:
            return False

        # Retrieve or initialize UTXO state for prior block
        unspent_outputs = self.utxo_state.get(prior_block.getHash(), None)
        if unspent_outputs is None:
            # genesis
            unspent_outputs = prior_block.validate({}, self.maxMintCoinsPerTx)
            if unspent_outputs is None:
                return False
            self.utxo_state[prior_block.getHash()] = unspent_outputs
        
        new_utxo_state = block.validate(unspent_outputs, self.maxMintCoinsPerTx)
        if new_utxo_state is None:
            return False

        # Append block to blockchain and store UTXO state
        self.blocks[block.getHash()] = block
        self.cumulative_work[block.getHash()] = (
            self.cumulative_work[block.getPriorBlockHash()] + self.getWork(block.getTarget())
        )
        self.utxo_state[block.getHash()] = new_utxo_state

        return True

# --------------------------------------------
# You should make a bunch of your own tests before wasting time submitting stuff to gradescope.
# Its a LOT faster to test locally.  Try to write a test for every API and think about weird cases.

# Let me get you started:
def Test():
    # test creating blocks, mining them, and verify that mining with a lower target results in a lower hash
    b1 = Block()
    b1.mine(int("F"*64,16))
    h1 = b1.getHash()
    b2 = Block()
    b2.mine(int("F"*63,16))
    h2 = b2.getHash()
    assert h2 < h1

    t0 = Transaction(None, [Output(lambda x: True, 100)])
    # Negative test: minted too many coins
    assert t0.validateMint(50) == False, "1 output: tx minted too many coins"
    # Positive test: minted the right number of coins
    assert t0.validateMint(100) == True, "1 output: tx minted the right number of coins"

    class GivesHash:
        def __init__(self, hash):
            self.hash = hash
        def getHash(self):
            return self.hash

    assert HashableMerkleTree([GivesHash(x) for x in [106874969902263813231722716312951672277654786095989753245644957127312510061509]]).calcMerkleRoot().to_bytes(32,"big").hex() == "ec4916dd28fc4c10d78e287ca5d9cc51ee1ae73cbfde08c6b37324cbfaac8bc5"
    
    assert HashableMerkleTree([GivesHash(x) for x in [106874969902263813231722716312951672277654786095989753245644957127312510061509, 66221123338548294768926909213040317907064779196821799240800307624498097778386, 98188062817386391176748233602659695679763360599522475501622752979264247167302]]).calcMerkleRoot().to_bytes(32,"big").hex() == "ea670d796aa1f950025c4d9e7caf6b92a5c56ebeb37b95b072ca92bc99011c20"

    print ("yay local tests passed")
