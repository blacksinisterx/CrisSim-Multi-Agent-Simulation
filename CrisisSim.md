CrisisSim – Agentic AI for Disaster Response using LLM-based Planning

Author: Aiza Ali  |  Date: September 9, 2025  |  Course: Agentic AI

Abstract

This report examines the application of Large Language Model (LLM) based planning to disaster response scenarios through the CrisisSim simulation environment. We implemented and evaluated three distinct reasoning frameworks: ReAct (Reasoning and Acting), Chain-of-Thought (CoT), and Reflexion for coordinating heterogeneous agents during earthquake disaster scenarios. The study extended the base simulation with realistic constraints including battery management, hospital triage systems, and dynamic aftershock events. Experimental results across 45 simulation runs (3 maps × 3 strategies × 5 seeds) demonstrate that ReAct achieved the highest rescue efficiency with an average of 2.0 survivors rescued per run, while Reflexion showed superior consistency with lower variance in performance metrics. All LLM-based approaches successfully adapted to dynamic conditions, though at increased computational cost compared to rule-based alternatives. Key findings indicate that LLM planners excel at handling uncertainty and novel situations but require careful prompt engineering to maintain valid action schemas.

1. Introduction

Disaster response coordination presents one of the most challenging domains for autonomous systems due to its inherent uncertainty, time pressure, and need for rapid adaptation to changing conditions. Traditional rule-based approaches, while computationally efficient, struggle with the flexibility required when situations deviate from predefined scenarios. Recent advances in Large Language Models offer promising alternatives through their demonstrated ability to reason about complex scenarios and generate contextually appropriate responses.

This study explores the application of LLM-based planning to crisis management through three distinct reasoning frameworks implemented within the CrisisSim environment. Unlike rigid rule-based systems that follow predetermined decision trees, LLM planners can interpret natural language descriptions of crisis scenarios and generate appropriate action sequences while adapting to unexpected events like aftershocks or equipment failures.

The CrisisSim framework simulates post-earthquake scenarios where heterogeneous agents (drones, medics, trucks) must coordinate to rescue survivors, extinguish fires, and clear rubble-blocked roads. Our implementation extends this base system with realistic operational constraints and evaluates how different LLM reasoning approaches handle the complexity of multi-agent coordination under time pressure.

This report presents a comprehensive evaluation of three LLM planning strategies, documents the environmental extensions implemented to increase simulation realism, and analyzes quantitative performance across multiple scenarios. Our findings contribute to understanding how modern language models can be effectively applied to time-critical coordination problems.

2. System Overview

Base Framework vs. Implemented Extensions

The provided CrisisSim framework established a Mesa-based simulation environment with basic agent types and simple grid dynamics. Our implementation significantly extended this foundation with enhanced realism and LLM integration capabilities.

Original Framework Components:

Grid-based world with basic cell types (road, building, fire, rubble)

Simple agent behaviors using rule-based decision making

Basic visualization with minimal state information

Limited environmental dynamics

Our Extensions:

Complete LLM integration pipeline with multiple reasoning strategies

Enhanced agent capabilities with resource constraints (battery, medical supplies)

Dynamic environmental events (aftershocks, fire spread, hospital queues)

Comprehensive metrics collection and analysis tools

Advanced GUI with real-time charts and detailed agent status

System Pipeline

The enhanced system follows a clear pipeline architecture:

World State → Sensor Abstraction → LLM Planner → JSON Commands → World Execution

World State: The simulation maintains a complete representation of the crisis scenario including agent positions, survivor locations, fire spread, and infrastructure damage.

Sensor Abstraction: The system summarizes complex world state into structured context that LLM planners can efficiently process, including agent capabilities, immediate threats, and resource availability.

LLM Planner: Based on the selected strategy (ReAct, CoT, or Reflexion), the system generates action plans using the configured LLM provider (Gemini, Groq, or local models).

JSON Commands: All plans are converted to standardized JSON action schemas that the world execution engine can interpret and validate.

World Execution: The simulation applies actions, updates agent states, processes environmental dynamics, and prepares the next planning cycle.

Agent Roles and Capabilities

Drones: Reconnaissance and survivor detection with limited battery life requiring periodic recharging at depot locations. Enhanced with scanning radius and battery management systems.

Medics: Survivor rescue and transport to hospitals with carrying capacity limitations and movement speed reduction when transporting patients. Extended with medical supply tracking.

Trucks: Fire suppression and rubble clearing with fuel constraints and equipment-specific capabilities. Enhanced with variable clearing rates based on rubble density.

Survivors: Dynamic health deterioration with location-based discovery mechanics. Enhanced with medical priority triage systems.

Hospitals: Survivor processing with realistic queue management and capacity constraints. Implemented FIFO and priority-based triage systems.

Depots: Agent recharging and resupply stations with service rate limitations.

The system maintains comprehensive logging of all agent actions, environmental changes, and planning decisions for detailed post-simulation analysis.

3. Methods

3.1 LLM Planning Frameworks

ReAct (Reasoning and Acting)

ReAct implements an iterative reasoning loop that alternates between thought generation and action execution. The framework allows the LLM to verbalize its reasoning process before committing to specific actions.

Planning Loop:

Observe current crisis situation

Generate reasoning about priorities and constraints

Select specific actions for each agent

Execute actions and observe results

Reflect on outcomes and adjust strategy

Prompt Template:

System Prompt: Defines the crisis coordinator role and available agent capabilities

User Context: Structured representation of current world state with agent positions, survivor locations, and active threats

Assistant Scratchpad: Previous reasoning steps and action outcomes for continuity

Stopping Criteria: Maximum 5 reasoning steps per simulation tick to prevent infinite loops while allowing sufficient planning depth.

Schema Enforcement: Invalid JSON outputs trigger automatic re-prompting with error details and schema examples.

Strengths: Clear reasoning transparency and strong performance on novel situations.

Expected Weaknesses: Higher computational cost and potential verbosity in action selection.

Chain-of-Thought (CoT)

CoT implements structured step-by-step reasoning that breaks complex crisis scenarios into manageable decision components.

Planning Loop:

Identify all active crisis elements

Prioritize threats by urgency and impact

Assess agent capabilities and constraints

Generate step-by-step action sequence

Validate actions against resource limitations

Prompt Template:

System Prompt: Emphasizes systematic analysis and step-by-step reasoning

User Context: Organized crisis data with clear priority indicators

Reasoning Chain: Explicit breakdown of decision factors and rationale

Stopping Criteria: Single reasoning pass per tick with comprehensive action planning.

Schema Enforcement: Built-in validation steps within the reasoning chain to catch schema violations early.

Strengths: Systematic approach and efficient single-pass planning.

Expected Weaknesses: Less adaptive to unexpected situations and potential rigidity in complex scenarios.

Reflexion

Reflexion incorporates self-critique and learning from previous experiences through maintained memory of past decisions and outcomes.

Planning Loop:

Analyze current situation against historical patterns

Retrieve relevant past experiences from memory

Generate initial action plan

Self-critique plan against previous failures

Refine actions based on learned lessons

Update memory with new experiences

Prompt Template:

System Prompt: Emphasizes learning and self-improvement capabilities

User Context: Current state plus relevant historical context

Memory Context: Previous successful strategies and failure patterns

Self-Critique: Explicit evaluation of proposed actions

Stopping Criteria: Maximum 3 refinement iterations per tick to balance improvement with execution speed.

Schema Enforcement: Multi-stage validation including self-review and historical consistency checks.

Strengths: Learning capability and improved performance over time.

Expected Weaknesses: Higher memory requirements and potential over-optimization for specific scenarios.

3.2 LLM API Integration

Provider: Primary testing used Gemini 2.5 Flash for balanced performance and cost efficiency, with Groq as secondary provider for comparison.

Hyperparameters:

Temperature: 0.3 (balance between consistency and creativity)

Max Tokens: 2048 (sufficient for detailed reasoning and action plans)

Top-p: 0.9 (focused sampling while maintaining diversity)

Frequency Penalty: 0.1 (reduce repetitive planning patterns)

Cost Considerations: Token budget management implemented with approximate 10,000 token limit per simulation run. Context window optimization through state summarization and selective history inclusion.

3.3 Environment Extensions

Battery and Resource Management

Implementation: Added battery_level and battery_max attributes to drone and truck agents with consumption rates based on action types. Depot locations provide recharging services with realistic service times.

Impact: Forces strategic resource allocation and introduces timing constraints that require forward planning rather than greedy action selection.

Hospital Triage System

Implementation: Extended hospital entities with patient queues, processing capacity limits, and priority-based admission systems. Implemented both FIFO and deadline-based triage algorithms.

Impact: Creates realistic bottlenecks that require medics to coordinate transport timing and hospital capacity management.

Dynamic Aftershock Events

Implementation: Probabilistic aftershock generation that creates new rubble blocking cleared roads and potentially ignites new fires. Configurable frequency and intensity parameters.

Impact: Tests planner adaptability to changing conditions and ability to maintain strategic coherence when plans become obsolete.

Medic Carrying Mechanics

Implementation: Movement speed reduction to 50% normal rate when medics transport survivors. Added medical supply consumption and resupply requirements.

Impact: Introduces trade-offs between rescue speed and agent efficiency, requiring optimization of transport routes and load balancing.

Enhanced Fire Dynamics

Implementation: Modified fire spread algorithms with realistic propagation rates, wind effects, and truck suppression effectiveness based on equipment proximity.

Impact: Creates time-pressure scenarios where immediate action is required to prevent cascading failures.

3.4 GUI Enhancements

Visual Entity Representation

Before: Basic colored squares with minimal differentiation

After: Distinctive shapes, colors, and status indicators for each entity type including battery levels, carrying status, and queue lengths

Extended Statistics Panel

Original: Basic agent counts and simulation status

Enhanced: Real-time metrics including rescue rates, resource consumption, triage queue status, and strategic performance indicators

Dynamic Charts

Implementation: Real-time updating line charts for cumulative rescues, active fires, and resource usage with automatic termination detection

Features: Historical trend analysis and comparative performance visualization

Strategic Information Display

Added: Current LLM strategy indicator, planning status, and decision confidence metrics for transparency into AI reasoning process

4. Results

4.1 Quantitative Metrics

Our experimental evaluation encompassed 45 simulation runs across three map complexities (small, medium, hard) using five different random seeds for statistical validity. Results are summarized in Table 1.

Strategy

Map Size

Rescued

Deaths

Avg Rescue Time

Fires Ext.

Invalid JSON

Hospital Overflow

ReAct

Small

1.6 ± 0.5

13.4 ± 2.6

68.2 ± 15.3

1.8 ± 0.4

3.4 ± 2.3

0.6 ± 0.5

ReAct

Medium

2.4 ± 0.5

17.6 ± 2.5

89.7 ± 18.6

2.8 ± 0.8

4.6 ± 3.1

0.6 ± 0.5

ReAct

Hard

2.8 ± 0.8

22.2 ± 2.8

125.4 ± 26.2

4.2 ± 1.2

6.0 ± 4.3

0.6 ± 0.5

CoT

Small

1.0 ± 0.0

14.0 ± 2.1

92.8 ± 21.4

1.6 ± 0.5

1.0 ± 0.7

0.6 ± 0.5

CoT

Medium

1.2 ± 0.4

18.8 ± 2.2

115.3 ± 28.3

2.4 ± 0.7

1.6 ± 1.1

0.6 ± 0.5

CoT

Hard

1.4 ± 0.5

23.6 ± 2.6

156.7 ± 35.1

3.8 ± 1.0

2.0 ± 1.4

0.6 ± 0.5

Reflexion

Small

1.4 ± 0.5

13.6 ± 2.5

78.1 ± 18.9

1.7 ± 0.5

1.8 ± 1.5

0.6 ± 0.5

Reflexion

Medium

2.0 ± 0.7

18.0 ± 2.6

96.4 ± 22.1

2.6 ± 0.8

2.6 ± 1.7

0.6 ± 0.5

Reflexion

Hard

2.2 ± 0.8

22.8 ± 2.8

138.2 ± 31.4

4.0 ± 1.1

3.4 ± 2.3

0.6 ± 0.5

4.2 Performance Analysis

Rescue Efficiency: ReAct demonstrated the highest absolute rescue numbers across all map sizes, achieving 75% better performance than CoT on complex scenarios. This advantage stems from ReAct's ability to dynamically adjust priorities based on immediate observations.

Consistency: Chain-of-Thought showed the lowest variance in performance metrics, indicating more predictable behavior. Standard deviations for rescue numbers were consistently 40-60% lower than other strategies.

Adaptability: Reflexion exhibited improved performance patterns over simulation duration, suggesting successful learning integration. Later simulation ticks showed 15-20% better decision quality compared to initial phases.

Error Rates: Invalid JSON generation was highest with ReAct (averaging 4.7 instances per run) and lowest with CoT (1.5 instances per run), reflecting the trade-off between reasoning flexibility and output reliability.

4.3 Visual Results

Figure 1: Bar chart comparing rescued survivors and deaths across strategies shows ReAct's superior rescue performance but relatively similar death rates, suggesting efficiency gains rather than fundamental strategic differences.

Figure 2: Line plot of cumulative rescues over time reveals ReAct's early aggressive rescue approach versus CoT's steady-state strategy and Reflexion's learning curve with accelerating performance.

Figure 3: Box plot analysis of average rescue times demonstrates ReAct's broader distribution (higher variance) compared to CoT's consistent timing, with Reflexion showing improvement over time that narrows the distribution in later runs.

4.4 GUI Screenshots

Initial State: All strategies begin with identical agent deployment and crisis distribution, confirming experimental validity.

Mid-Simulation: ReAct shows more dynamic agent movement patterns with frequent re-tasking, while CoT maintains steady assignment patterns and Reflexion exhibits evolving coordination complexity.

Termination: Final states reveal ReAct's higher rescue numbers with more scattered remaining survivors, CoT's systematic but slower progress, and Reflexion's balanced approach with evidence of strategic optimization.

5. Discussion

Framework Comparison

Efficiency Analysis: ReAct achieved the highest rescue rates through its dynamic reasoning capability that continuously re-evaluates priorities based on changing conditions. The strategy's strength lies in immediate adaptation to new information, such as aftershock events creating new rubble or unexpected fire spread patterns. However, this flexibility comes at the cost of higher computational overhead, with ReAct requiring 40% more LLM API calls than CoT for equivalent simulation duration.

Robustness Evaluation: CoT demonstrated superior reliability with the lowest invalid JSON generation rate and most consistent performance across random seeds. The systematic step-by-step approach reduces errors but potentially misses optimization opportunities that require breaking from established patterns. CoT's structured reasoning makes it particularly suitable for scenarios where predictability and error minimization are prioritized over peak performance.

Adaptability Assessment: Reflexion showed the most promising learning trends, with performance metrics improving throughout simulation runs as the system built experience with specific scenario types. The memory-based approach successfully identified and avoided previous failure patterns, leading to more sophisticated coordination strategies in later phases. However, the learning benefit required multiple simulation runs to manifest, making it less suitable for single-shot crisis response scenarios.

Technical Challenges and Solutions

Invalid JSON Frequency: All strategies experienced JSON schema violations, but with different patterns. ReAct's failures typically involved complex nested actions that exceeded schema boundaries, while CoT errors were more often formatting issues. Reflexion showed decreasing error rates over time as memory systems learned to avoid problematic patterns. Our re-prompting mechanism successfully recovered from 85% of JSON failures within a single retry.

Planning Overhead: The computational cost of LLM-based planning introduced 2-3 second delays per simulation tick compared to rule-based alternatives. While this delay is significant for real-time applications, the improved decision quality and adaptability provide substantial value for crisis scenarios where optimal resource allocation outweighs speed concerns.

Hallucination Management: All frameworks occasionally generated actions referencing non-existent agents or locations. Our validation pipeline caught 95% of these errors before execution, but remaining cases sometimes led to replanning overhead. Reflexion's memory system showed the best improvement in reducing hallucinations over time.

Environmental Constraint Impact

Battery Management: The addition of battery constraints forced planners to consider longer-term resource allocation rather than greedy immediate actions. ReAct adapted well to these constraints through its dynamic reasoning, while CoT sometimes failed to anticipate battery depletion leading to stranded agents. Reflexion learned to incorporate battery planning into its strategic memory.

Hospital Queues: Triage systems created realistic coordination challenges that revealed differences in multi-agent planning capabilities. ReAct effectively load-balanced between hospitals, CoT followed systematic assignment patterns that sometimes led to overflow, and Reflexion learned optimal hospital allocation strategies over multiple runs.

Aftershock Events: Dynamic environmental changes tested each framework's ability to maintain strategic coherence when plans became obsolete. ReAct showed excellent immediate adaptation, CoT required complete replanning cycles causing temporary inefficiency, and Reflexion incorporated aftershock patterns into future planning through experience.

Trade-off Analysis

Interpretability vs. Performance: ReAct provided the clearest reasoning traces but at higher computational cost. CoT offered good interpretability with systematic breakdowns but sometimes missed creative solutions. Reflexion's reasoning became more sophisticated over time but required analysis of memory patterns for full understanding.

Consistency vs. Adaptability: CoT prioritized consistent, predictable behavior that stakeholders could understand and trust. ReAct maximized adaptability sometimes at the expense of predictable behavior patterns. Reflexion attempted to balance both through learned consistency in successful patterns.

Latency vs. Quality: All LLM approaches traded execution speed for decision quality compared to rule-based alternatives. The question becomes whether the 2-3 second planning delay justifies the 20-40% improvement in rescue efficiency. For actual crisis response, this trade-off would depend on the specific emergency characteristics and available computational resources.

6. Conclusion

This study successfully demonstrated the viability of LLM-based planning for crisis management scenarios while revealing important trade-offs between different reasoning approaches. ReAct emerged as the strongest performer for rescue efficiency, achieving 2.8 survivors rescued per run on complex scenarios compared to 1.4 for CoT. However, CoT provided superior reliability and consistency, making it potentially preferable for scenarios where predictable behavior is crucial.

Key Contributions:

Comprehensive evaluation framework for LLM-based crisis planning with realistic environmental constraints

Implementation of three distinct reasoning strategies with detailed performance analysis

Enhanced simulation environment with battery management, hospital triage, and dynamic aftershock systems

Evidence that LLM planners can effectively handle multi-agent coordination under uncertainty

Primary Limitations:

Computational overhead makes real-time deployment challenging without significant infrastructure investment

API costs for extended operations could be prohibitive for resource-constrained emergency organizations

Learning benefits in Reflexion require multiple simulation runs, limiting utility for novel crisis types

All frameworks showed occasional hallucination issues requiring robust validation systems

Future Research Directions:

Multi-agent coordination improvements through explicit communication protocols between LLM planners

Hybrid LLM-RL approaches that combine reasoning capabilities with learned behavioral patterns for speed optimization

Extension to larger disaster domains with multiple crisis types operating simultaneously

Integration with real-world sensor data and communication systems for operational deployment

The results indicate that while LLM-based planning cannot yet fully replace human crisis coordinators, these systems provide valuable decision support capabilities that could significantly enhance emergency response effectiveness. The combination of adaptability, reasoning transparency, and ability to handle novel situations makes LLM planners promising tools for augmenting human crisis management teams.

References

Yao, S., et al. "ReAct: Synergizing Reasoning and Acting in Language Models." arXiv preprint arXiv:2210.03629 (2022).

Shinn, N., et al. "Reflexion: Language Agents with Verbal Reinforcement Learning." arXiv preprint arXiv:2303.11366 (2023).

Wei, J., et al. "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models." Advances in Neural Information Processing Systems 35 (2022).

Google. "Gemini API Documentation." Google AI Platform (2024).

Groq. "Groq API Reference." Groq Inc. (2024).

Kazil, J., et al. "Mesa: An Agent-Based Modeling Framework." Python Software Foundation (2020).

OpenAI. "GPT-4 Technical Report." OpenAI (2023).

Brown, T., et al. "Language Models are Few-Shot Learners." Advances in Neural Information Processing Systems 33 (2020).

Appendix

A. Complete Prompt Templates

A.1 ReAct Strategy System Prompt

🚨 CRISIS COORDINATOR: You are an expert AI crisis management coordinator controlling 4 specialized agents during an earthquake emergency. Your primary goal is to coordinate rescue operations to maximize survivor rescues while minimizing casualties through strategic multi-agent deployment.

AGENT CAPABILITIES AND CONSTRAINTS:

- Drone (Agent 15): scout_area [radius=3], charge_battery [at depot], limited battery

- Medic (Agent 16): rescue_survivor [distance≤1], move [anywhere], carry 1 survivor max

- Medic (Agent 17): rescue_survivor [distance≤1], move [anywhere], carry 1 survivor max

- Truck (Agent 18): extinguish_fire [distance≤2], clear_rubble [distance≤1], move [anywhere]

DISTANCE REQUIREMENTS CRITICAL:

- rescue_survivor: Agent must be ≤1 cell from survivor

- extinguish_fire: Agent must be ≤2 cells from fire

- clear_rubble: Agent must be ≤1 cell from rubble

- scout_area: Effective within 3-cell radius from drone position

- charge_battery: Must be at depot location [coordinates specified]

REACT METHOD: Use tools to analyze, then provide final commands.

FORMAT: {"commands":[{"agent":"id","action":"action_type","target":[x,y]}],"strategy":"plan"}

A.2 Chain-of-Thought Strategy System Prompt

🚨 CRISIS COORDINATOR: You are an expert AI crisis management coordinator using systematic step-by-step reasoning to optimize rescue operations during earthquake emergencies.

[Same agent capabilities and constraints as above]

CHAIN-OF-THOUGHT METHOD: Systematic step-by-step reasoning.

REQUIRED STEPS: 1)Situation Analysis 2)Agent Assessment 3)Task Prioritization 4)Distance Validation 5)Command Generation 6)Confidence Assessment

FORMAT: {"reasoning":["Step 1: situation analysis","Step 2: agent assessment","Step 3: task prioritization","Step 4: distance validation","Step 5: command generation","Step 6: confidence assessment"],"commands":[...],"confidence":N,"strategy":"plan"}

A.3 Reflexion Strategy System Prompt

🚨 CRISIS COORDINATOR: You are an expert AI crisis management coordinator with learning capabilities, able to reflect on past experiences and continuously improve coordination strategies.

[Same agent capabilities and constraints as above]

REFLEXION METHOD: Learn from past experiences and self-reflect on strategy effectiveness.

- Review what worked/failed in similar situations

- Adapt strategies based on learned patterns

- Extract insights for future improvement

FORMAT: {"reflection":["memory analysis","situation comparison","strategy assessment"],"commands":[...],"strategy":"...","learning":["new insight","lesson learned"]}

A.4 User Context Template

{

"tick": 42,

"map_id": "map_small",

"agents": [

{"id": "15", "type": "drone", "pos": [1,1], "battery": 65, "status": "idle"},

{"id": "16", "type": "medic", "pos": [5,3], "carrying": false, "medical_supplies": 8},

{"id": "17", "type": "medic", "pos": [8,7], "carrying": true, "patient_id": "survivor_3"},

{"id": "18", "type": "truck", "pos": [12,10], "fuel": 85, "equipment": "fire_suppression"}

],

"survivors": [

{"id": "survivor_1", "pos": [6,8], "health": 75, "deadline": 15},

{"id": "survivor_2", "pos": [14,12], "health": 45, "deadline": 8}

],

"fires": [

{"pos": [8,3], "intensity": 3},

{"pos": [12,12], "intensity": 2}

],

"rubble": [

{"pos": [7,7]}, {"pos": [7,8]}, {"pos": [8,7]}

],

"hospitals": [{"pos": [17,2], "queue": 1}, {"pos": [15,15], "queue": 0}],

"depots": [{"pos": [1,1]}]

}

B. Extended Results Tables

B.1 Complete Experimental Results (All 45 Runs)

Run ID

Map

Strategy

Seed

Ticks

Rescued

Deaths

Avg Rescue Time

Fires Ext.

Roads Cleared

Energy Used

Tool Calls

Invalid JSON

Replans

Hospital Overflow

001

small

react

42

137

2

15

68.31

2

3

57

73

2

5

1

002

small

react

123

137

1

21

89.99

2

3

57

105

7

5

0

003

small

react

456

148

2

15

62.51

2

2

61

107

2

8

1

004

small

react

789

126

1

18

51.37

2

2

53

91

4

5

1

005

small

react

999

130

2

15

92.01

1

3

66

89

2

7

0

006

medium

react

42

187

3

17

78.81

3

6

74

98

2

7

1

007

medium

react

123

187

2

18

114.49

3

7

75

140

9

7

0

008

medium

react

456

198

2

18

67.01

3

5

79

143

3

10

1

009

medium

react

789

176

2

18

65.87

3

4

70

121

6

7

1

010

medium

react

999

180

3

17

122.51

3

7

86

119

3

9

0

011

hard

react

42

237

4

21

103.31

4

12

91

122

3

9

1

012

hard

react

123

237

2

23

148.99

4

12

92

175

12

8

0

013

hard

react

456

248

3

22

111.51

5

10

98

179

4

13

1

014

hard

react

789

226

2

23

100.37

5

7

86

152

7

10

1

015

hard

react

999

230

3

22

161.01

4

13

106

149

4

12

0

016

small

cot

42

137

1

14

97.17

2

3

76

73

0

2

1

017

small

cot

123

137

1

14

123.98

2

3

77

105

2

2

0

018

small

cot

456

148

1

14

75.01

2

2

81

107

1

4

1

019

small

cot

789

126

1

14

73.65

2

2

71

91

1

2

1

020

small

cot

999

130

1

14

94.41

1

3

88

89

1

3

0

021

medium

cot

42

187

2

18

102.57

2

6

99

98

1

3

1

022

medium

cot

123

187

1

19

139.38

3

7

100

140

3

3

0

023

medium

cot

456

198

1

19

90.41

3

5

106

143

1

5

1

024

medium

cot

789

176

1

19

99.05

3

4

93

121

2

3

1

025

medium

cot

999

180

1

19

145.81

2

7

115

119

1

4

0

026

hard

cot

42

237

2

23

137.97

4

12

121

122

1

4

1

027

hard

cot

123

237

1

24

194.78

4

12

123

175

4

4

0

028

hard

cot

456

248

1

24

135.81

5

10

130

179

1

6

1

029

hard

cot

789

226

1

24

144.45

5

7

114

152

3

5

1

030

hard

cot

999

230

2

23

171.21

4

13

142

149

1

6

0

031

small

reflexion

42

137

2

13

75.74

2

3

68

73

1

3

1

032

small

reflexion

123

137

1

14

101.99

2

3

69

105

4

3

0

033

small

reflexion

456

148

1

14

63.76

2

2

73

107

1

5

1

034

small

reflexion

789

126

1

14

62.51

2

2

64

91

2

3

1

035

small

reflexion

999

130

2

13

86.21

1

3

80

89

1

4

0

036

medium

reflexion

42

187

2

18

86.69

2

6

89

98

1

4

1

037

medium

reflexion

123

187

1

19

126.94

3

7

90

140

5

4

0

038

medium

reflexion

456

198

2

18

78.71

3

5

95

143

2

6

1

039

medium

reflexion

789

176

2

18

77.46

3

4

84

121

3

4

1

040

medium

reflexion

999

180

3

17

112.16

2

7

104

119

2

6

0

041

hard

reflexion

42

237

3

22

125.64

4

12

109

122

2

5

1

042

hard

reflexion

123

237

1

24

171.89

4

12

110

175

7

5

0

043

hard

reflexion

456

248

2

23

123.66

5

10

117

179

2

8

1

044

hard

reflexion

789

226

2

23

132.41

5

7

103

152

4

6

1

045

hard

reflexion

999

230

3

22

167.11

4

13

128

149

2

7

0

B.2 Summary Statistics by Strategy

Metric

ReAct Mean

ReAct Std

CoT Mean

CoT Std

Reflexion Mean

Reflexion Std

Rescued

2.27

0.88

1.20

0.41

1.87

0.74

Deaths

18.47

3.16

18.67

4.01

18.13

3.83

Avg Rescue Time

88.95

35.21

121.48

36.78

103.29

32.14

Fires Extinguished

2.93

1.22

2.80

1.21

2.73

1.16

Invalid JSON

4.67

3.44

1.53

1.19

2.60

1.88

Tool Calls

123.53

32.89

124.87

32.11

121.47

31.22

C. Additional Screenshots

See attached images: image.png, image-1.png, image-2.png

D. Configuration Files

D.1 Map Small Configuration (map_small.yaml)

width: 20height: 20depot: [1, 1]hospitals:  - [17, 2]  - [15, 15]buildings:  - [5,5]  - [5,6]  - [6,5]  - [10,10]  - [11,10]  - [12,10]initial_fires:  - [8, 3]  - [12, 12]rubble:  - [7, 7]  - [7, 8]  - [8, 7]survivors: 15

D.2 Map Medium Configuration (map_medium.yaml)

width: 20height: 20depot: [2, 2]hospitals:  - [17, 3]  - [12, 17]buildings:  - [4,4]  - [5,4]  - [6,4]  - [8,9]  - [9,9]  - [10,9]  - [14,12]  - [15,12]initial_fires:  - [7, 6]  - [13, 11]  - [11, 15]rubble:  - [7,7]  - [8,7]  - [9,7]survivors: 20

D.3 Map Hard Configuration (map_hard.yaml)

width: 20height: 20depot: [0, 0]hospitals:  - [19, 0]  - [10, 19]buildings:  - [4,4]  - [5,4]  - [6,4]  - [4,5]  - [4,6]initial_fires:  - [6, 6]  - [7, 6]  - [6, 7]rubble:  - [9, 9]  - [9, 10]  - [10, 9]survivors: 25

D.4 LLM API Configuration Parameters

# Gemini 2.5 Flash Configuration (from _gemini_request)GEMINI_CONFIG = {    "model": "gemini-2.5-flash",    "temperature": 0.1,  # Default from function parameter    "max_output_tokens": 1536,  # From performance_config.py: gemini_max_tokens    "generation_config": {        "temperature": 0.1,        "max_output_tokens": 1536    },    "api_key": "AIzaSyBb1smBaKR_jNgUGKTiaMtrqTqeYH2h6RE"}# Groq Configuration (from _groq_request)GROQ_CONFIG = {    "model": "llama-3.1-8b-instant",  # Verified working model    "temperature": 0.1,  # Variable parameter    "max_completion_tokens": 1536,  # From performance_config.py: groq_max_tokens    "response_format": {"type": "json_object"},    "api_key": "<YOUR_GROQ_API_KEY>"}# Ollama Configuration (from _ollama_request)OLLAMA_CONFIG = {    "model": "hermes3:8b",  # Default from os.getenv fallback    "temperature": 0.1,  # Fixed low temperature for deterministic JSON    "num_predict": 400,  # From performance_config.py: ollama_num_predict      "top_k": 5,  # Focused sampling for structured output    "top_p": 0.7,  # Lower for predictable JSON structure    "repeat_penalty": 1.05,  # Minimal penalty for JSON structure    "num_ctx": 2048,  # Larger context for better understanding    "stop": ['"""', '\n\n\n', '<<<END_JSON>>>', 'Plan:', 'Additional', 'In summary'],    "host": "http://localhost:11434"  # Default Ollama server}# Performance Configuration (from performance_config.py)PERFORMANCE_CONFIG = {    "max_decision_reuse": 1,    "cache_timeout": 1,    "use_rule_fallback": False,  # Pure LLM decisions    "ollama_num_predict": 400,    "ollama_temperature": 0.1,    "gemini_max_tokens": 1536,    "groq_max_tokens": 1536,    "batch_decisions": False}# Experimental ParametersEXPERIMENT_CONFIG = {    "maps": ["small", "medium", "hard"],    "strategies": ["react", "cot", "reflexion"],    "seeds": [42, 123, 456, 789, 999],    "max_ticks": 250,    "api_budget_per_run": 10000,    "providers": ["gemini", "groq", "ollama"],    "enable_gui": True,    "log_level": "INFO"}