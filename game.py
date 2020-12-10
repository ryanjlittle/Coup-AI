# This is a very simple Python 2.7 implementation of the Information Set Monte Carlo Tree Search algorithm.
# The function ISMCTS(rootstate, itermax, verbose = False) is towards the bottom of the code.
# It aims to have the clearest and simplest possible code, and for the sake of clarity, the code
# is orders of magnitude less efficient than it could be made, particularly by using a 
# state.GetRandomMove() or state.DoRandomRollout() function.
# 
# An example GameState classes for Knockout Whist is included to give some idea of how you
# can write your own GameState to use ISMCTS in your hidden information game.
# 
# Written by Peter Cowling, Edward Powley, Daniel Whitehouse (University of York, UK) September 2012 - August 2013.
# 
# Licence is granted to freely use and distribute for any sensible/legal purpose so long as this comment
# remains in any distributed code.
# 
# For more information about Monte Carlo Tree Search check out our web site at www.mcts.ai
# Also read the article accompanying this code at ***URL HERE***

from math import *
import random
from copy import deepcopy
from itertools import combinations


class GameState:
    """ A state of the game, i.e. the game board. These are the only functions which are
        absolutely necessary to implement ISMCTS in any imperfect information game,
        although they could be enhanced and made quicker, for example by using a
        GetRandomMove() function to generate a random move during rollout.
        By convention the players are numbered 1, 2, ..., self.numberOfPlayers.
    """

    def __init__(self):
        self.numberOfPlayers = 2
        self.playerToMove = 1

    def GetNextPlayer(self, p):
        """ Return the player to the left of the specified player
        """
        return (p % self.numberOfPlayers) + 1

    def Clone(self):
        """ Create a deep clone of this game state.
        """
        st = GameState()
        st.playerToMove = self.playerToMove
        return st

    def CloneAndRandomize(self, observer):
        """ Create a deep clone of this game state, randomizing any information not visible to the specified observer player.
        """
        return self.Clone()

    def DoMove(self, move):
        """ Update a state by carrying out the given move.
            Must update playerToMove.
        """
        self.playerToMove = self.GetNextPlayer(self.playerToMove)

    def GetMoves(self):
        """ Get all possible moves from this state.
        """
        raise NotImplementedError()

    def GetResult(self, player):
        """ Get the game result from the viewpoint of player.
        """
        raise NotImplementedError()

    def __repr__(self):
        """ Don't need this - but good style.
        """
        pass


class CoupState(GameState):

    def __init__(self, n):
        """ Initialize the game state. n is the number of players (from 2 to 6).
        """
        self.numberOfPlayers = n + 1  # We need an extra player for the environment player
        self.playerToMove = 1
        self.playerHands = {p: [] for p in range(self.numberOfPlayers + 1)}
        self.coins = {p: 2 for p in range(1, self.numberOfPlayers + 1)}  # Players start with 2 coins
        # Stores the cards that have been revealed
        self.revealedCards = {"Ambassador": 0, "Assassin": 0, "Captain": 0, "Contessa": 0, "Duke": 0}
        self.knockedOut = {p: False for p in range(1, self.numberOfPlayers + 1)}
        # The current action in play
        self.currentAction = None
        self.currentActionPlayer = None
        self.currentActionTarget = None
        # The current block in play
        self.currentBlock = None
        self.currentBlockPlayer = None
        self.challenger = None
        # Indicates if the players are currently being asked to challenge the ongoing action
        self.challengingPhase = False
        # self.blockingPhase = False
        # Indicates if the current player is revealing an influence
        self.revealingInfluence = False
        # Indicates if the current player is choosing a target for the current action
        self.choosingTarget = False
        # Holds the 2 cards drawn when playing ambassador
        self.ambassadorCards = []

        self.Deal()

    def Clone(self):
        """ Create a deep clone of this game state.
        """
        st = CoupState(self.numberOfPlayers - 1)  # Subtract 1 because of the environment player
        st.playerToMove = self.playerToMove
        st.playerHands = deepcopy(self.playerHands)
        st.revealedCards = deepcopy(self.revealedCards)
        st.coins = deepcopy(self.coins)
        st.currentAction = self.currentAction
        st.currentActionPlayer = self.currentActionPlayer
        st.currentActionTarget = self.currentActionTarget
        st.currentBlock = self.currentBlock
        st.currentBlockPlayer = self.currentBlockPlayer
        st.challenger = self.challenger
        st.challengingPhase = self.challengingPhase
        st.revealingInfluence = self.revealingInfluence
        st.choosingTarget = self.choosingTarget
        st.knockedOut = deepcopy(self.knockedOut)
        st.ambassadorCards = deepcopy(self.ambassadorCards)

        return st

    def CloneAndRandomize(self, observer):
        """ Create a deep clone of this game state, randomizing any information not visible to the specified observer player.
                """
        st = self.Clone()

        # Count up all the seen cards
        seenCount = st.revealedCards
        for card in st.playerHands[observer]:
            seenCount[card] = seenCount.get(card, 0) + 1

        # Remove all seen cards from a standard Coup deck
        unseenCards = st.GetCardDeck()
        for card in unseenCards:
            if seenCount.get(card, 0) > 0:
                unseenCards.remove(card)
                seenCount[card] -= 1

        # Deal the unseen cards to the other players
        random.shuffle(unseenCards)
        for p in range(1, st.numberOfPlayers):
            if p != observer:
                # Deal cards to player p
                # Store the size of player p's hand
                numCards = len(self.playerHands[p])
                # Give player p the first numCards unseen cards
                st.playerHands[p] = unseenCards[: numCards]
                # Remove those cards from unseenCards
                unseenCards = unseenCards[numCards:]

        return st

    def CloneAndSelfDeterminize(self):
        """ Create a deep clone of this game state, randomizing all non-public information.
                """
        st = self.Clone()

        seenCount = self.revealedCards

        # Remove all seen cards from a standard Coup deck
        unseenCards = st.GetCardDeck()
        for card in unseenCards:
            if seenCount.get(card, 0) > 0:
                unseenCards.remove(card)
                seenCount[card] -= 1

        # Deal the unseen cards to the players
        random.shuffle(unseenCards)
        for p in range(1, st.numberOfPlayers):
            # Deal cards to player p
            # Store the size of player p's hand
            numCards = len(self.playerHands[p])
            # Give player p the first numCards unseen cards
            st.playerHands[p] = unseenCards[: numCards]
            # Remove those cards from unseenCards
            unseenCards = unseenCards[numCards:]

        return st

    def GetCardDeck(self):
        return ["Ambassador", "Assassin", "Captain", "Contessa", "Duke"] * 3

    def Deal(self):
        """ Reset the game state for the beginning of a new round, and deal the cards.
        """
        self.revealedCards = {"Ambassador": 0, "Assassin": 0, "Captain": 0, "Contessa": 0, "Duke": 0}
        self.coins = {p: 2 for p in range(1, self.numberOfPlayers)}

        # Construct a deck, shuffle it, and deal it to the players
        deck = self.GetCardDeck()
        random.shuffle(deck)
        # Deal two cards to each player
        for p in range(1, self.numberOfPlayers):
            self.playerHands[p] = deck[:2]
            deck = deck[2:]

    def DealFromDeck(self, n):
        # Count up all the revealed cards and cards in players hands
        cardCount = self.revealedCards
        for player in range(1, self.numberOfPlayers):
            for card in self.playerHands[player]:
                cardCount[card] = cardCount.get(card, 0) + 1

        # Remove all seen cards from a standard Coup deck
        deckCards = self.GetCardDeck()
        for card in deckCards:
            if cardCount.get(card, 0) > 0:
                deckCards.remove(card)
                cardCount[card] -= 1

        random.shuffle(deckCards)
        return deckCards[:n]

    def ResolveChallenge(self):
        if self.currentBlock is not None:
            # If the blocker is not bluffing, the challenger loses influence
            if self.currentBlock in self.playerHands[self.currentBlockPlayer]:
                self.playerToMove = self.challenger
                # The blocking player discards their card and draws another
                self.playerHands[self.currentBlockPlayer].remove(self.currentBlock)
                self.playerHands[self.currentBlockPlayer] += self.DealFromDeck(1)
                # print("PLAYER %i REVEALS A %s AND DRAWS A NEW CARD" % (self.currentBlockPlayer, self.currentBlock))
            else:
                self.playerToMove = self.currentBlockPlayer
            self.challengingPhase = False
            self.revealingInfluence = True

        elif self.currentAction is not None:
            self.challengingPhase = False
            self.revealingInfluence = True
            # If the action player is not bluffing
            if self.currentAction in self.playerHands[self.currentActionPlayer]:
                self.playerToMove = self.challenger
                # The action player discards their card and draws another
                self.playerHands[self.currentActionPlayer].remove(self.currentAction)
                self.playerHands[self.currentActionPlayer] += self.DealFromDeck(1)
                # print("PLAYER %i REVEALS A %s AND DRAWS A NEW CARD" % (self.currentActionPlayer, self.currentAction))
            else:
                self.playerToMove = self.currentActionPlayer

        # print("PLAYER %i LOST THE CHALLENGE AND MUST REVEAL INFLUENCE" % self.playerToMove)
        return

    def Challenge(self):
        # print("PLAYER %i CHALLENGES" % self.playerToMove)

        # Let the environment player resolve the challenge.
        self.challenger = self.playerToMove
        self.challengingPhase = False
        self.playerToMove = 0
        return

    def Allow(self):
        self.playerToMove = self.GetNextPlayer(self.playerToMove)
        # If we are in the challenging a block phase
        if self.currentBlock is not None:
            # Skip over the player who blocked
            if self.playerToMove == self.currentBlockPlayer:
                self.playerToMove = self.GetNextPlayer(self.playerToMove)
            # All players have had a chance to challenge and we are back to the target of the block
            if self.playerToMove == self.currentActionPlayer:
                # The block went unchallenged, so no action happens and we go to the next player's turn
                self.playerToMove = self.GetNextPlayer(self.currentActionPlayer)
                self.ResetAction()
            return

        if self.challengingPhase:
            # If the action is targetable, the order of challenges is different.
            if self.currentActionTarget is not None:
                # Skip over the player who played the action
                if self.playerToMove == self.currentActionPlayer:
                    self.playerToMove = self.GetNextPlayer(self.playerToMove)
                # If every player chooses not to block
                if self.playerToMove == self.currentActionTarget:
                    self.challengingPhase = False
                    self.EnactAction(self.currentAction)
            # The action is nontargetable
            else:
                if self.playerToMove == self.currentActionPlayer:
                    self.challengingPhase = False
                    self.EnactAction(self.currentAction)
        return

    def Income(self):
        self.coins[self.currentActionPlayer] += 1
        self.playerToMove = self.GetNextPlayer(self.currentActionPlayer)
        self.ResetAction()
        return

    def ForeignAid(self):
        self.coins[self.currentActionPlayer] += 2
        self.playerToMove = self.GetNextPlayer(self.currentActionPlayer)
        self.ResetAction()
        return

    def Coup(self):
        self.coins[self.currentActionPlayer] = self.coins[self.currentActionPlayer] - 7
        self.playerToMove = self.currentActionTarget
        self.revealingInfluence = True

    def Ambassador(self):
        self.ambassadorCards = self.DealFromDeck(2)
        return

    def Assassin(self):
        if not self.knockedOut[self.currentActionTarget]:
            self.playerToMove = self.currentActionTarget
            self.revealingInfluence = True
        # This case happens when the target loses their last card blocking or challenging an assassination
        else:
            self.playerToMove = self.GetNextPlayer(self.currentActionPlayer)
            self.ResetAction()
        return

    def Captain(self):
        stolenCoins = min(2, self.coins[self.currentActionTarget])
        self.coins[self.currentActionTarget] -= stolenCoins
        self.coins[self.currentActionPlayer] += stolenCoins
        self.playerToMove = self.GetNextPlayer(self.currentActionPlayer)
        self.ResetAction()
        return

    def Duke(self):
        self.coins[self.currentActionPlayer] += 3
        self.playerToMove = self.GetNextPlayer(self.currentActionPlayer)
        self.ResetAction()

    def DoMove(self, move):
        # The cards that can block each action
        blocks = {"Ambassador": [], "Assassin": ["Contessa"], "Captain": ["Ambassador", "Captain"], "Contessa": [],
                  "Coup": [], "Duke": [], "Income": [], "Foreign Aid": ["Duke"]}
        challengable = {"Ambassador": True, "Assassin": True, "Captain": True, "Contessa": True, "Coup": False,
                        "Duke": True, "Income": False, "Foreign Aid": False}
        targetted = {"Ambassador": False, "Assassin": True, "Captain": True, "Contessa": True, "Coup": True,
                     "Duke": False, "Income": False, "Foreign Aid": False}

        if self.revealingInfluence:
            self.playerHands[self.playerToMove].remove(move)
            self.revealedCards[move] += 1
            self.revealingInfluence = False
            # print("PLAYER %i REVEALS A %s" % (self.playerToMove, move))

            if len(self.playerHands[self.playerToMove]) <= 0:
                self.knockedOut[self.playerToMove] = True
            # If the bluffing player was blocking an action, the action happens now
            if self.currentBlock is not None:
                if self.playerToMove == self.currentBlockPlayer:
                    self.currentBlock = None
                    self.currentBlockPlayer = None
                    self.EnactAction(self.currentAction)
                    return
            elif self.currentAction is not None and self.currentAction != "Coup":
                # If the player incorrectly challenged an action, enact the action now.
                if self.playerToMove == self.challenger:
                    self.playerToMove = self.currentActionPlayer
                    self.EnactAction(self.currentAction)
                    return

            self.playerToMove = self.GetNextPlayer(self.currentActionPlayer)
            self.ResetAction()
            return

        if self.choosingTarget:
            self.currentActionTarget = int(move)
            self.choosingTarget = False
            # A coup is not blockable or challengable, so the target immediately loses influence.
            if self.currentAction == "Coup":
                self.EnactAction(self.currentAction)
            # If the action is not a coup, ask the other players if they want to block/challenge
            else:
                self.playerToMove = self.currentActionTarget
                self.challengingPhase = True
            return

        if self.ambassadorCards != []:
            self.playerHands[self.currentActionPlayer] = list(move)
            self.ambassadorCards = []
            self.playerToMove = self.GetNextPlayer(self.currentActionPlayer)
            self.ResetAction()
            return

        if self.currentAction is None:
            self.currentAction = move
            self.currentActionPlayer = self.playerToMove
            # We need to subtract coins here because the coins should be paid even if it is blocked.
            if move == "Assassin":
                self.coins[self.currentActionPlayer] -= 3
            if targetted[move]:
                self.choosingTarget = True
            elif challengable[move] or blocks[move] != []:
                self.challengingPhase = True
                self.playerToMove = self.GetNextPlayer(self.playerToMove)
            else:
                self.EnactAction(move)
            return

        # If the player plays a block
        if self.challengingPhase and move not in ["Allow", "Challenge"]:
            self.challengingPhase = False
            self.currentBlock = move
            self.currentBlockPlayer = self.playerToMove
            self.playerToMove = self.currentActionPlayer
            return

        self.EnactAction(move)

    def EnactAction(self, action):
        switcher = {
            "Resolve Challenge": self.ResolveChallenge,
            "Challenge": self.Challenge,
            "Allow": self.Allow,
            "Income": self.Income,
            "Foreign Aid": self.ForeignAid,
            "Coup": self.Coup,
            "Ambassador": self.Ambassador,
            "Assassin": self.Assassin,
            "Captain": self.Captain,
            "Duke": self.Duke
        }

        func = switcher.get(action, lambda: print("INVALID MOVE"))
        func()

    def GetNextPlayer(self, p):
        """ Return the player to the left of the specified player, skipping players who have been knocked out
        """
        next = (p % (self.numberOfPlayers - 1)) + 1
        # Skip any knocked-out players
        while next != p and self.knockedOut[next]:
            next = (next % (self.numberOfPlayers - 1)) + 1
        return next

    def ResetAction(self):
        self.currentAction = None
        self.currentActionPlayer = None
        self.currentActionTarget = None
        self.currentBlock = None
        self.currentBlockPlayer = None
        self.challenger = None

    def GetMoves(self):

        # If all opponents are knocked out, return no moves.
        if all(self.knockedOut[i] for i in range(1, self.numberOfPlayers) if i != self.playerToMove):
            return []

        # Player 0 is the environment player. Their only move is to resolve challenges.
        if self.playerToMove == 0:
            return ["Resolve Challenge"]

        if self.revealingInfluence:
            return self.playerHands[self.playerToMove]

        if self.choosingTarget:
            return [str(i) for i in range(1, self.numberOfPlayers) if i != self.playerToMove and not self.knockedOut[i]]

        if self.currentBlock is not None:
            return ["Allow", "Challenge"]

        if self.challengingPhase:
            # The cards that can block each action
            blocks = {"Ambassador": [], "Assassin": ["Contessa"], "Captain": ["Ambassador", "Captain"], "Contessa": [],
                      "Coup": [], "Duke": [], "Income": [], "Foreign Aid": ["Duke"]}
            challengable = {"Ambassador": True, "Assassin": True, "Captain": True, "Contessa": True, "Coup": False,
                            "Duke": True, "Income": False, "Foreign Aid": False}
            # Filter out possible blocks if all 3 cards are revealed.
            options = ["Allow"] + [card for card in blocks[self.currentAction] if self.revealedCards[card] < 3]
            if challengable[self.currentAction]:
                options += ["Challenge"]
            return options

        if self.ambassadorCards != []:
            possibleCards = self.ambassadorCards + self.playerHands[self.playerToMove]
            handLength = len(self.playerHands[self.currentActionPlayer])
            # Return the possible hands after discarding. Identical hands are ignored.
            return list(set(combinations(possibleCards, handLength)))

        # If the player has 10 or more coins, they must coup.
        if self.coins[self.playerToMove] >= 10:
            return ["Coup"]

        # Standard turn options. Assassin and coup are only available if the player has enough money.
        options = ["Income", "Foreign Aid", "Duke", "Captain", "Ambassador"]
        if self.coins[self.playerToMove] >= 3:
            options += ["Assassin"]
        if self.coins[self.playerToMove] >= 7:
            options += ["Coup"]
        # Filter out options where all 3 cards are already revealed
        return [opt for opt in options if self.revealedCards.get(opt, 0) < 3]

    def GetResult(self, player):
        """ Get the game result from the viewpoint of player.
        """
        # Environment player always receives a reward of 0
        if player == 0:
            return 0
        return 0 if (self.knockedOut[player]) else 1

    def __repr__(self):
        """ Return a human-readable representation of the state
        """
        result = ""
        # for player in range(1, self.numberOfPlayers):
        #     result += " | P%i: " % player
        #     result += ", ".join(card for card in self.playerHands[player])
        result += " | P%i: " % self.playerToMove
        result += ", ".join(self.playerHands[self.playerToMove])
        #
        # result += " | P%i: " % self.playerToMove
        # result += ", ".join(action.name for action in self.playerHands[self.playerToMove])
        result += " | Coins: ["
        result += ", ".join(("P%i: %i" % (player, self.coins[player])) for player in range(1, self.numberOfPlayers))
        result += "]"

        # result += "\n Challenging: "
        # result += "Y" if self.challengingPhase else "N"
        # result += "\n Blocking: "
        # result += "Y" if self.blockingPhase else "N"
        # result += "\n Revealing: "
        # result += "Y" if self.revealingInfluence else "N"
        # result += "\n Ambasssador cards: "
        # for card in self.ambassadorCards:
        #     result += card
        # result += "\n P" + str(self.playerToMove) + "'s turn to move"

        return result


class Node:
    """ A node in the game tree. Note wins is always from the viewpoint of playerJustMoved.
    """

    def __init__(self, move=None, parent=None, playerJustMoved=None):
        self.move = move  # the move that got us to this node - "None" for the root node
        self.parentNode = parent  # "None" for the root node
        self.childNodes = []
        self.wins = 0
        self.visits = 0
        self.avails = 1
        self.playerJustMoved = playerJustMoved  # the only part of the state that the Node needs later

    def GetUntriedMoves(self, legalMoves):
        """ Return the elements of legalMoves for which this node does not have children.
        """

        # Find all moves for which this node *does* have children
        triedMoves = [child.move for child in self.childNodes]

        # Return all moves that are legal but have not been tried yet
        return [move for move in legalMoves if move not in triedMoves]

    def UCBSelectChild(self, legalMoves, exploration=0.7):
        """ Use the UCB1 formula to select a child node, filtered by the given list of legal moves.
            exploration is a constant balancing between exploitation and exploration, with default value 0.7 (approximately sqrt(2) / 2)
        """

        # Filter the list of children by the list of legal moves
        legalChildren = [child for child in self.childNodes if child.move in legalMoves]

        # Get the child with the highest UCB score
        s = max(legalChildren,
                key=lambda c: float(c.wins) / float(c.visits) + exploration * sqrt(log(c.avails) / float(c.visits)))

        # Update availability counts -- it is easier to do this now than during backpropagation
        for child in legalChildren:
            child.avails += 1

        # Return the child selected above
        return s

    def AddChild(self, m, p):
        """ Add a new child node for the move m.
            Return the added child node
        """
        n = Node(move=m, parent=self, playerJustMoved=p)
        self.childNodes.append(n)
        return n

    def Update(self, terminalState):
        """ Update this node - increment the visit count by one, and increase the win count by the result of terminalState for self.playerJustMoved.
        """
        self.visits += 1
        if self.playerJustMoved is not None:
            self.wins += terminalState.GetResult(self.playerJustMoved)

    def __repr__(self):
        return "[M:%s W/V/A: %4i/%4i/%4i]" % (self.move, self.wins, self.visits, self.avails)

    def TreeToString(self, indent):
        """ Represent the tree as a string, for debugging purposes.
        """
        s = self.IndentString(indent) + str(self)
        for c in self.childNodes:
            s += c.TreeToString(indent + 1)
        return s

    def IndentString(self, indent):
        s = "\n"
        for i in range(1, indent + 1):
            s += "| "
        return s

    def ChildrenToString(self):
        s = ""
        for c in self.childNodes:
            s += str(c) + "\n"
        return s


def ISMCTS(rootstate, itermax, verbose=False, exploration=0.7):
    """ Conduct an ISMCTS search for itermax iterations starting from rootstate.
        Return the best move from the rootstate.
    """

    rootnode = Node()

    for i in range(itermax):
        node = rootnode

        # Determinize
        state = rootstate.CloneAndRandomize(rootstate.playerToMove)

        # Select
        # node is fully expanded and non-terminal
        while state.GetMoves() != [] and node.GetUntriedMoves( state.GetMoves()) == []:
            node = node.UCBSelectChild(state.GetMoves(), exploration=exploration)
            state.DoMove(node.move)

        # Expand
        untriedMoves = node.GetUntriedMoves(state.GetMoves())
        if untriedMoves != []:  # if we can expand (i.e. state/node is non-terminal)
            m = random.choice(untriedMoves)
            player = state.playerToMove
            state.DoMove(m)
            node = node.AddChild(m, player)  # add child and descend tree

        # Simulate
        while state.GetMoves() != []:  # while state is non-terminal
            state.DoMove(random.choice(state.GetMoves()))

        # Backpropagate
        while node != None:  # backpropagate from the expanded node and work back to the root node
            node.Update(state)
            node = node.parentNode

    # Output some information about the tree - can be omitted
    if (verbose):
        print(rootnode.TreeToString(0))
    #else:
        #print(rootnode.ChildrenToString())

    return max(rootnode.childNodes, key=lambda c: c.visits).move  # return the move that was most visited

def ISMCTS_Split(rootstate, itermax, verbose=False, exploration=0.7):
    """ Conduct an ISMCTS search for itermax iterations starting from rootstate.
        Return the best move from the rootstate.
    """

    rootnode = Node()

    for i in range(itermax):
        node = rootnode

        # Determinize. The first half of iterations self determinizes, and the second half does not.
        if i < itermax * 0.7:
            state = rootstate.CloneAndSelfDeterminize()
        else:
            state = rootstate.CloneAndRandomize(rootstate.playerToMove)

        # Select
        # node is fully expanded and non-terminal
        while state.GetMoves() != [] and node.GetUntriedMoves( state.GetMoves()) == []:
            node = node.UCBSelectChild(state.GetMoves(), exploration=exploration)
            state.DoMove(node.move)

        # Expand
        untriedMoves = node.GetUntriedMoves(state.GetMoves())
        if untriedMoves != []:  # if we can expand (i.e. state/node is non-terminal)
            m = random.choice(untriedMoves)
            player = state.playerToMove
            state.DoMove(m)
            node = node.AddChild(m, player)  # add child and descend tree

        # Simulate
        while state.GetMoves() != []:  # while state is non-terminal
            state.DoMove(random.choice(state.GetMoves()))

        # Backpropagate
        while node != None:  # backpropagate from the expanded node and work back to the root node
            node.Update(state)
            node = node.parentNode



    # Output some information about the tree - can be omitted
    if (verbose):
        print(rootnode.TreeToString(0))
    #else:
        #print(rootnode.ChildrenToString())

    return max(rootnode.childNodes, key=lambda c: c.visits).move  # return the move that was most visited



def playCoup():
    """ Play a sample game between two Coup players.
    """
    state = CoupState(2)
    state.playerToMove = random.randint(1, 2)

    while (state.GetMoves() != []):
        # print(str(state))
        # Use different numbers of iterations (simulations, tree nodes) for different players
        if state.playerToMove == 1:
            m = ISMCTS(rootstate=state, itermax=10000, verbose=False, exploration=1.5)
        elif state.playerToMove == 2:
            m = ISMCTS_Split(rootstate=state, itermax=10000, verbose=False, exploration=1.5)
        elif state.playerToMove == 3:
            m = random.choice(state.GetMoves())
        else:
            m = ISMCTS(rootstate=state, itermax=1, verbose=False)
            # m = ISMCTS(rootstate=state, itermax=500, verbose=False, exploration=1.25)
        # print("Best Move: " + str(m) + "\n")
        state.DoMove(m)

    for i in range(1, state.numberOfPlayers):
        if not state.knockedOut[i]:
            # print("Player %i won!" % i)
            return i


if __name__ == "__main__":
    # tally = {1:0, 2:0, 3:0, 4:0, 5:0}
    # for _ in range(1000):
    #     winner = playCoup()
    #     tally[winner] += 1
    #     print(tally)

    state = CoupState(2)
    state.playerHands[1] = ["Contessa", "Contessa"]
    choices = {state: 0 for state in state.GetMoves()}
    for _ in range(100):
        m = ISMCTS_Split(rootstate=state, itermax=20000, verbose=False, exploration=1.5)
        choices[m] += 1
        print(choices)

    # print("Best Move: " + str(m) + "\n")
    # # state.playerToMove = 2
    # # state.currentAction = "Captain"
    # # state.currentActionPlayer = 1
    # # state.currentActionTarget = 2
    # # state.challengingPhase = True
    # # state.blockingPhase = False
    # # state.revealingInfluence = False
    # # state.choosingTarget = False
    # # state.revealedCards["Ambassador"] = 3
    #


    for x in range(1000):
        state = CoupState(3)

        while state.GetMoves() != []:
            print(state)
            moves = state.GetMoves()
            print(moves)
            # move = random.choice(moves)
            move = int(input("Which move?"))
            print(move)
            state.DoMove(moves[move])
        print(x)

    # PlayGame()
