export const meta = {
  name: 'agents-core-report-judge',
  description: 'Blind yes/no judging of agents final messages against each task rubric',
  phases: [{ title: 'Judge' }, { title: 'Write' }],
}

const DIR = args.dir
const COUNT = args.count

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

phase('Judge')
const judged = await parallel(numbers.map(n => () =>
  agent(`You are grading one final message written by a coding agent at the end of a task. Read exactly one file: ${DIR}/item-${n}.json
It holds "message" (the agent's final message) and "questions" (each with an id and a yes/no question). Answer every question with yes or no, judging only from the text of the message. Do not give the benefit of the doubt: answer yes only when the message plainly does what the question asks. Read nothing else and change nothing.`, { label: `judge:${n}`, phase: 'Judge', schema: ANSWERS, model: 'sonnet', effort: 'low', agentType: 'general-purpose' })
    .then(r => r && { item: n, answers: r.answers })))

const all = judged.filter(Boolean)

phase('Write')
await agent(`Write the JSON between the markers, exactly as it is, to the file ${DIR}/answers.json using the Write tool. Then reply DONE.
<<<BEGIN
${JSON.stringify(all)}
END>>>`, { label: 'write:answers', phase: 'Write', model: 'haiku', effort: 'low', agentType: 'general-purpose' })

return { judged: all.length, of: COUNT }
