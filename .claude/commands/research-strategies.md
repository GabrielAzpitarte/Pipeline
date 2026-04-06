Research trading strategies for IMC Prosperity. Focus area: $ARGUMENTS

Steps:
1. Search the web for relevant strategies:
   - "IMC Prosperity $ARGUMENTS strategy"
   - "algorithmic trading $ARGUMENTS"
   - Look at winning teams' GitHub repos and writeups

2. For each strategy found, summarize:
   - What it does (1-2 sentences)
   - When it works (what market conditions)
   - When it fails
   - Key parameters to tune
   - How to implement it in our framework (using `compute_orders(state)`)

3. Check if the strategy fits our current products and backtester:
   - Can it be tested with our `SimEngine`?
   - Does it need data we don't have?

4. If promising, suggest adding it to `src/agents/prompts/playbook.md`

5. If very promising, implement it:
   - Create the strategy file using `/add-strategy`
   - Backtest it on the practice data
   - Report the results
