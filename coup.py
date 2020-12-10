from game import *
import matplotlib.pyplot as plt


def PlayAgainstCPU():
    state = CoupState(5)

    state.playerToMove = 3
    print(state.coins)
    state.coins = {1: 7, 2: 2, 3:11, 4:9}
    print(state.coins)



    while state.GetMoves() != []:
        # The CPU
        if state.playerToMove == 1:
            move = ISMCTS_Split(rootstate=state, itermax=1000, verbose=False, exploration=1.5)
            try:
                print("CPU plays " + move)
            except:
                pass
            state.DoMove(move)
        # The enviroment player's turn
        elif state.playerToMove == 0:
            state.DoMove(state.GetMoves()[0])
        # A human player's turn
        else:
            print(str(state))
            moves = state.GetMoves()
            for i, m in enumerate(moves):
                print("%i: %s" % (i+1, m))
            move = int(input("Which move?"))
            state.DoMove(moves[move-1])
    print(str(state))
    for i in range(1, state.numberOfPlayers):
        if not state.knockedOut[i]:
            print("Player %i won!" % i)


def PlayAsCPU():
    state = CoupState(4)

    state.playerToMove = 3
    print(state.coins)
    state.coins = {1: 7, 2: 2, 3: 11, 4: 9}
    print(state.coins)

    aiPlayer = 1
    players = ["Ryan", "Brian", "Brandon", "Anna"]
    for i, p in enumerate(players):
        print("%i: %s" % (i+1, p))
    state.playerToMove = int(input("Who goes first?"))

    cards = ["Ambassador", "Assassin", "Captain", "Contessa", "Duke"]
    print("What are your two cards?")
    for i, c in enumerate(cards):
        print("%i: %s" % (i+1, c))
    card1 = cards[int(input())-1]
    card2 = cards[int(input())-1]
    state.playerHands[aiPlayer] = [card1, card2]

    while state.GetMoves() != []:
        if state.playerToMove == aiPlayer:
            if state.ambassadorCards != []:
                print("What are the ambassador cards?")
                for i, c in enumerate(cards):
                    print("%i: %s" % (i + 1, c))
                card1 = cards[int(input()) - 1]
                card2 = cards[int(input()) - 1]
                state.ambassadorCards = [card1, card2]
            print(str(state))
            moves = state.GetMoves()
            for i, m in enumerate(moves):
                print("%i: %s" % (i + 1, m))
            move = ISMCTS(rootstate=state, itermax=10000, verbose=False, exploration=2.0)
            print("AI says " + str(move))
            i = input("Press enter to play")
            # This is a cheat to redeal your cards. Useful when you discard and are automatically assigned a new card.
            if i == 'r':
                print("What are your two cards?")
                for i, c in enumerate(cards):
                    print("%i: %s" % (i + 1, c))
                card1 = cards[int(input()) - 1]
                card2 = cards[int(input()) - 1]
                state.playerHands[aiPlayer] = [card1, card2]
                continue
            state.DoMove(move)
        elif state.playerToMove == 0:
            if state.currentBlock is not None:
                print("%s says %s's %s is a bluff." % (players[state.challenger-1], players[state.currentBlockPlayer-1], state.currentBlock))
                response = input("Does %s have a %s? (y/n)" % (players[state.currentBlockPlayer-1], state.currentBlock))
                if response.upper() == "Y":
                    # Give the blocker the correct card
                    state.playerHands[state.currentBlockPlayer][0] = state.currentBlock
                elif response.upper() == "N":
                    # Otherwise make sure they don't have the correct card
                    while state.currentBlock in state.playerHands[state.currentBlockPlayer]:
                        state.playerHands[state.currentBlockPlayer].remove(state.currentBlock)
                        state.playerHands[state.currentBlockPlayer] += CoupState.DealFromDeck(state, 1)
            else:
                print("%s says P%s's %s is a bluff." % (players[state.challenger-1], players[state.currentActionPlayer-1], state.currentAction))
                response = input("Does %s have a %s? (y/n)" % (players[state.currentActionPlayer-1], state.currentAction))
                if response.upper() == "Y":
                    # Give the blocker the correct card
                    state.playerHands[state.currentActionPlayer][0] = state.currentAction
                elif response.upper() == "N":
                    # Otherwise make sure they don't have the correct card
                    while state.currentAction in state.playerHands[state.currentActionPlayer]:
                        state.playerHands[state.currentActionPlayer].remove(state.currentAction)
                        state.playerHands[state.currentActionPlayer] += CoupState.DealFromDeck(state, 1)
            state.DoMove("Resolve Challenge")
        else:
            print(players[state.playerToMove-1])
            if state.revealingInfluence:
                for i, c in enumerate(cards):
                    print("%i: %s" % (i + 1, c))
                card = cards[int(input("What card does %s reveal?" % players[state.playerToMove-1])) - 1]
                # give that player the card they revealed
                state.playerHands[state.playerToMove][0] = card
                # Have them reveal it
                state.DoMove(card)
                continue

            print(str(state))
            moves = state.GetMoves()
            for i, m in enumerate(moves):
                print("%i: %s" % (i + 1, m))
            move = int(input("Which move?"))
            state.DoMove(moves[move - 1])




if __name__ == "__main__":
    PlayAsCPU()
