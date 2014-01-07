import random
import environments as env
from math import log

def _f2p(fList):
	"""
	Private method for calculating probabilities for
	each value in a given list fList
	"""
	pDict = {}
	n = len(fList)
	for val in fList:
		# calculate frequencies for each value
		pDict.setdefault(val, 0)
		pDict[val] += 1
	# return probabilities
	return dict((val, freq / n) for val, freq in pDict)


def _alpha(n):
	"""
	The step size function to ensure convergence. The
	function decreases as the number of times a state
	has been visited increases (n). It means that the
	utility of policy pi for state s will converge to
	correct value.
	"""
	return 50. / (49 + n)


def _getEstimates(transs, utils, currState, currActions=None):
	"""
	Gets estimates according to current transition states,
	utility, current state and actions that can be executed
	in current state.

	transs keys:
	currState => actions => newState
	
	For every possible action in currState
		- get frequencies newState|currState,action
		- count them: n
		- get probabilities: divide freqs with n
		- calculate estimate with bellman
	
	Return (rewardEstimate, action) pairs in a dict
	"""

	estimates = []
	for ac in (currActions or transs.get(currState, {})):
		freq = transs.get(currState, {}).get(ac, {})
		# Number of states.
		n = sum(val for val in freq.values())
		probs = dict((key, float(val) / n) for key, val in freq.iteritems())
		estimates.append((sum(p * utils.get(s, 0) for s, p in probs.iteritems()), ac, ))
	return estimates


def _getEstimatesOptimistic(transs, utils, currState, R_plus, N_e, currActions=None):
	"""
	Gets estimates for optimistic.

	Return (rewardEstimate, action) pairs in a dict
	"""

	estimates = []
	for ac in (currActions or transs.get(currState, {})):
		# We get N_s_a from transition table.
		freq = transs.get(currState, {}).get(ac, {})

		# Number of states.
		n = sum(val for val in freq.values())
		probs = dict((key, float(val) / n) for key, val in freq.iteritems())
		u = sum(p * utils.get(s, 0) for s, p in probs.iteritems())

		# This if function f from page 842.
		if n < N_e:
			estimates.append((R_plus, ac, ))
		else:
			estimates.append((u, ac, ))
	return estimates

def adp_random_exploration(env, transs={}, utils={}, freqs={}, **kwargs):
	"""
	Active ADP (adaptive dynamic programming) learning
	algorithm which returns the best policy for a given
	environment env and experience dictionary exp

	The experience dictionary exp can be empty if 
	the agent has no experience with the environment
	but can also be full with values from
	previous trials

	The algorithm returns the number of iterations
	needed to reach a terminal state

	For reference look in page 834.

	@param env: Environment
	@param transs: A transition table (N_s'_sa) with outcome frequencies given state action pairs, initially zero.
	@param utils: Utilities table
	@param freqs: A table of frequencies (N_sa) for state-action pairs, initially zero.
	@param t: A parameter for choosing best action or random action.
	@param tStep: A step to increment parameter t.
	@param alpha: Step size function
	@param maxItr: Maximum iterations
	"""

	t = kwargs.get('t', 1)
	tStep = kwargs.get('tStep', 0.8)
	alpha = kwargs.get('alpha', _alpha)
	maxItr = kwargs.get('maxItr', 50)
	
	itr = 0
	isTerminal = False
	state = env.getStartingState()

	# Start reward should be zero.
	reward = 0

	# Get possible actions with respect to current state.
	actions = env.getActions(state)
	rewardEstimate, bestAction = None, None
	if len(utils) > 0: # if this is not the first trial
		rewardEstimate, bestAction = max(_getEstimates(transs, utils, state, actions))

	while not isTerminal: # while not terminal
		if random.random() < 1. / log(t+1) or bestAction is None:
			# If it is the first iteration or exploration event
			# then randomly choose an action. Taking a random action in 1/t instances.
			bestAction = random.choice(actions)

		# do the action with the best policy
		# or do some random exploration
		newState, new_reward, isTerminal = env.do(state, bestAction)

		# Set to zero if newState does not exist yet. For new state?
		freqs.setdefault(newState, 0)
		freqs[newState] += 1

		# update transition table. The first one returns dictionary of actions for specific state and the
		# second one a dictionary of possible states from specific action (best action).
		transs.setdefault(state, {}).setdefault(bestAction, {}).setdefault(newState, 0)
		transs[state][bestAction][newState] += 1

		# We need to get actions on current state!
		actions = env.getActions(state)
		rewardEstimate, bestAction = max(_getEstimates(transs, utils, state, actions))

		# Update utility: Bellman equation
		utils[state] = reward + _alpha(freqs.get(state, 0)) * rewardEstimate

		# Is this part from the book:
		# Having obtained a utility function U that is optimal for the learned model,
		# the agent can extract an optimal action by one-step look-ahead to maximize
		# the expected utility; alternatively, if it uses policy iteration, the
		# optimal policy is already available, so it should simply execute the
		# action the optimal policy recommends. Or should it?
		new_actions = env.getActions(newState)
		rewardEstimate, bestAction = max(_getEstimates(transs, utils, newState, new_actions))

		actions = new_actions
		state = newState
		reward = new_reward

		# A GLIE scheme must also eventually become greedy, so that the agent's actions
		# become optimal with respect to the learned (and hence the true) model. That is
		# why the parameter t needs to be incremented.
		t, itr = t + tStep, itr + 1
		if itr >= maxItr:
			break
	return itr


def adp_random_exploration_state(env, transs={}, utils={}, freqs={}, **kwargs):
	"""
	Active ADP learning algorithm which returns the best
	policy for a given environment env and experience
	dictionary exp

	The experience dictionary exp can be empty if 
	the agent has no experience with the environment
	but can also be full with values from
	previous trials

	The algorithm returns the number of iterations
	needed to reach a terminal state
	"""
	alpha = kwargs.get('alpha', _alpha)
	maxItr = kwargs.get('maxItr', 50)
	
	itr = 0
	isTerminal = False
	state = env.getStartingState()

	reward = 0
	actions = env.getActions(state)
	rewardEstimate, bestAction = None, None
	# Also not clear how this contributes to better performance.
	# if len(utils) > 0: # if this is not the first trial
	#	rewardEstimate, bestAction = max(_getEstimates(transs, utils, state, actions))

	while not isTerminal: # while not terminal
		t = float(len(freqs)) or 1.
		if random.random() < 1. / (t+1) or bestAction is None:
			# If it is the first iteration or exploration event
			# then randomly choose an action
			bestAction = random.choice(actions)

		# do the action with the best policy
		# or do some random exploration
		newState, new_reward, isTerminal = env.do(state, bestAction)

		# Not sure which frequency should we increment (new state or current state)?
		# When testing it works better if using new state!
		freqs.setdefault(newState, 0)
		freqs[newState] += 1

		# update transition table
		transs.setdefault(state, {}).setdefault(bestAction, {}).setdefault(newState, 0)
		transs[state][bestAction][newState] += 1

		actions = env.getActions(state)
		rewardEstimate, bestAction = max(_getEstimates(transs, utils, state, actions))
		
		# Update utility
		utils[state] = reward + _alpha(freqs.get(state, 0)) * rewardEstimate

		new_actions = env.getActions(newState)
		rewardEstimate, bestAction = max(_getEstimates(transs, utils, newState, new_actions))

		actions = new_actions
		state = newState
		reward = new_reward

		itr += 1
		if itr >= maxItr:
			break
	return itr


def adp_optimistic_rewards(env, transs={}, utils={}, freqs={}, **kwargs):
	"""
	Active ADP (adaptive dynamic programming)

	@param env: Environment
	@param transs: A transition table (N_s'_sa) with outcome frequencies given state action pairs, initially zero.
	@param utils: Utilities table
	@param freqs: A table of frequencies (N_sa) for state-action pairs, initially zero.
	@param R_plus: An optimistic estimate of the best possible reward obtainable in any state.
	@param N_e: Limit of how many number of optimistic reward is given before true utility.
	@param alpha: Step size function
	@param maxItr: Maximum iterations
	"""
	R_plus = kwargs.get('R_plus', 5)
	N_e = kwargs.get('N_e', 12)
	alpha = kwargs.get('alpha', _alpha)
	maxItr = kwargs.get('maxItr', 10)

	itr = 0
	isTerminal = False
	state = env.getStartingState()

	# Start reward should be zero.
	reward = 0

	# Get possible actions with respect to current state.
	actions = env.getActions(state)
	rewardEstimate, bestAction = None, None
	if len(utils) > 0: # if this is not the first trial
		rewardEstimate, bestAction = max(_getEstimatesOptimistic(transs, utils, state, R_plus, N_e, actions))

	while not isTerminal: # while not terminal
		if bestAction is None:
			# If it is the first iteration or exploration event
			# then randomly choose an action. Taking a random action in 1/t instances.
			bestAction = random.choice(actions)

		# do the action with the best policy
		# or do some random exploration
		newState, new_reward, isTerminal = env.do(state, bestAction)

		# Set to zero if newState does not exist yet. For new state?
		freqs.setdefault(newState, 0)
		freqs[newState] += 1

		# update transition table. The first one returns dictionary of actions for specific state and the
		# second one a dictionary of possible states from specific action (best action).
		transs.setdefault(state, {}).setdefault(bestAction, {}).setdefault(newState, 0)
		transs[state][bestAction][newState] += 1

		# We need to get actions on current state!
		actions = env.getActions(state)
		rewardEstimate, bestAction = max(_getEstimatesOptimistic(transs, utils, state, R_plus, N_e, actions))

		# Update utility: Bellman equation
		utils[state] = reward + _alpha(freqs.get(state, 0)) * rewardEstimate

		# Is this part from the book:
		# Having obtained a utility function U that is optimal for the learned model,
		# the agent can extract an optimal action by one-step look-ahead to maximize
		# the expected utility; alternatively, if it uses policy iteration, the
		# optimal policy is already available, so it should simply execute the
		# action the optimal policy recommends. Or should it?
		new_actions = env.getActions(newState)
		rewardEstimate, bestAction = max(_getEstimatesOptimistic(transs, utils, newState, R_plus, N_e, new_actions))

		actions = new_actions
		state = newState
		reward = new_reward

		itr += 1
		if itr >= maxItr:
			break
	return itr


# Agent class.
class Agent():
	def __init__(self):
		self.clearExperience()

	def clearExperience(self):
		# Frequency table.
		self.nTable = {}

		# Transition table.
		self.transTable = {}

		# Utilities table.
		self.uTable = {}

		# Results
		self.results = []

	def getPolicy(self):
		policy = {}
		# For every state set appropriate action.
		for state in self.transTable:
			policy[state] = max(_getEstimates(self.transTable, self.uTable, state))[1]
		return policy

	def learn(self, env, alg=adp_random_exploration, numOfTrials=150, **kwargs):
		"""
		Learn best policy given the environment, algorithm and number of trials.
		@param env:
		@param alg:
		@param numOfTrials:
		"""
		
		
		itrs = 0
		self.clearExperience()
		for trial in range(numOfTrials):
			itrs += alg(env,
						transs=self.transTable,
						utils=self.uTable,
						freqs=self.nTable,
						currItrs=itrs,
						results=self.results,
						**kwargs)
		return self.getPolicy()

	def solve(self, env, policy):
		# solve environment with respect to policy
		actions, energy = [], 0

		# Set state to starting state of environment.
		state, prevState = env.getStartingState(), None
		isTerminalState = False
		while not isTerminalState:
		# Policy has best actions for given state.
			act = policy.get(state)
			if act is None:
				act = random.choice(env.getActions(state))
				# Execute selected action in current state.
			state, reward, isTerminalState = env.do(state, act)

			actions.append(act)
			energy += reward

			if energy < -1000:
				break
			# We get a list of actions that were executed and sum of rewards that were given when agent entered certain state.
		return actions, energy

# lets test it on boxworld2
"""
a = Agent()
a.learn(env.boxworld1, alg=adp_optimistic_rewards)
env.boxworld1.printPolicy(a.getPolicy())

# get solution and print it for this simple example
solution = a.solve(env.boxworld1, a.getPolicy())
print "Solution steps: " + str(solution)

# print solution steps
state = env.boxworld1.getStartingState()
for move in solution[0]:
	env.boxworld1.printState(state)
	state, reward, is_terminal = env.boxworld1.do(state, move)
env.boxworld1.printState(state)
"""
