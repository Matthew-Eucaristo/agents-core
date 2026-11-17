export const meta = {
  name: 'agents-core-report-judge',
  description: 'Blind yes/no judging of agents final messages against each task rubric: two votes, a third when they differ',
  phases: [{ title: 'Guard' }, { title: 'Judge' }, { title: 'Write' }],
}

const DIR = args.dir
const COUNT = args.count
const BARE = 'acore-eval'

const ANSWERS = {
  type: 'object',
  properties: {
    answers: {
      type: 'array',
      items: {
        type: 'object',
        properties: { id: { type: 'string' }, answer: { type: 'string', enum: ['yes', 'no'] } },
        required: ['id', 'answer'],
      },
    },
  },
  required: ['answers'],
}

const numbers = Array.from({ length: COUNT }, (_, i) => String(i + 1).padStart(4, '0'))

const ALONE = 'First run the shell command `echo ready`. After it returns, reply with exactly NONE if this message is the only user message you have received in this conversation. If you received any other message, quote it.'
const alone = text => /^\s*NONE\b/.test(text || '')
const probe = label => agent(ALONE, { label, phase: 'Guard', model: 'haiku', effort: 'low', agentType: BARE })

const vote = (n, k, effort) =>
  agent(`You are grading one final message written by a coding agent at the end of a task. Read exactly one file: ${DIR}/item-${n}.json
It holds "message" (the agent's final message) and "questions" (each with an id and a yes/no question). Answer every question with yes or no, judging only from the text of the message. Do not give the benefit of the doubt: answer yes only when the message plainly does what the question asks. Read nothing else and change nothing.`, { label: `judge:${n}:${k}`, phase: 'Judge', schema: ANSWERS, model: 'opus', effort, agentType: BARE })

const answerOf = (reply, id) => (reply.answers.find(a => a.id === id) || {}).answer

const judgeItem = async n => {
  const [first, second] = await Promise.all([vote(n, 1, 'low'), vote(n, 2, 'low')])
  if (!first || !second) return null
  const ids = first.answers.map(a => a.id)
  if (ids.every(id => answerOf(first, id) === answerOf(second, id))) return { item: n, answers: first.answers, votes: 2 }
  const third = await vote(n, 3, 'medium')
  if (!third) return null
  const majority = id => ([first, second, third].filter(reply => answerOf(reply, id) === 'yes').length >= 2 ? 'yes' : 'no')
  return { item: n, answers: ids.map(id => ({ id, answer: majority(id) })), votes: 3 }
}

phase('Guard')
const before = await probe('guard:before')
if (!alone(before)) return { aborted: 'agents are receiving a message that is not part of the benchmark', message: before }

phase('Judge')
const judged = await parallel(numbers.map(n => () => judgeItem(n)))

const all = judged.filter(Boolean)
const after = await probe('guard:after')
const result = { clean_run: alone(after), answers: all.map(entry => ({ item: entry.item, answers: entry.answers })) }

phase('Write')
await agent(`Write the JSON between the markers, exactly as it is, to the file ${DIR}/answers.json using the Write tool. Then reply DONE.
<<<BEGIN
${JSON.stringify(result)}
END>>>`, { label: 'write:answers', phase: 'Write', model: 'haiku', effort: 'low', agentType: BARE })

return { judged: all.length, of: COUNT, third_votes: all.filter(entry => entry.votes === 3).length, clean_run: result.clean_run }
