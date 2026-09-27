---
layout: post
title: How many labels is a good description worth?
date: 2026-09-28 00:30:00+0200
description: I compared Jev, a model you only describe the task to, with classical classifiers trained on up to 4,000 labels. On topics and intents it matched them; on emotions it lost, and the reason says a lot about confidence.
tags: machine learning, uncertainty modeling
categories: experiments
related_posts: false
permalink: /blog/2026/how-many-labels-is-a-description-worth/
---

On news topics, a model that never saw a single labeled example matched classifiers trained on 4,000 of them. On emotions in tweets, it lost to classifiers trained on a few hundred. That gap taught me more than either score.

I've spent a lot of time with generative models, so an AI model that gives up generating text caught my attention. Jev, from TypeSafe AI, doesn't write an answer. You give it some text, a question and a set of allowed answers, and it returns a choice with probabilities. That raises a question I keep coming back to: how much of the work we give language models actually needs a generated response?

First impressions are cheap, so I ran an experiment. I asked the most practical question I could think of: **how many labeled examples does a classical classifier need before it catches up with a model you only describe the task to?**

## Isn't this just classification?

Partly, yes. A classifier takes an input and returns a label with a probability; we've done that for decades. The difference is how you define the task. A supervised classifier learns one mapping from labeled examples, and changing the categories usually means relabeling and retraining. With Jev, you describe the decision and the possible answers in plain language. Several questions can be asked about the same context at once ([TypeSafe documentation](https://docs.typesafe.ai/introduction)).

The promise is LLM-like flexibility behind an interface that feels like a classifier. The [*Jev in the Wild*](https://arxiv.org/html/2609.30216v1) paper places it in exactly that gap, between task-specific classifiers and generative models. Zero-shot classification isn't new, and neither are probabilities. My question also echoes Le Scao and Rush's [*How Many Data Points is a Prompt Worth?*](https://aclanthology.org/2021.naacl-main.208/), which measured the same trade-off for prompted fine-tuning. What deserves testing is whether this combination of flexibility, speed, cost and decision quality makes new applications practical.

## The experiment

I picked three well-known public datasets that ask very different things of a classifier:

| Dataset | Task | Categories | Test texts |
| --- | --- | ---: | ---: |
| [AG News](https://huggingface.co/datasets/fancyzhx/ag_news) | Topic of a news article | 4 | 400 |
| [Banking77](https://huggingface.co/datasets/PolyAI/banking77) | Intent of a bank customer's message | 77 | 770 |
| [Emotion](https://huggingface.co/datasets/dair-ai/emotion) | Emotion expressed in a short English post | 6 | 300 |

On one side, five classical models: logistic regression, Naive Bayes, a linear SVM and two XGBoost variants, all on TF-IDF text features. Each was trained on increasing amounts of labeled data, from 5 to 1,000 examples per category, repeated with three random samples. Hyperparameters were tuned on a separate validation set.

On the other side, Jev (`jev-1.13.0`), with **no training examples at all**. For each text it received only the category names and a one-line description of each, such as "Sports news: games, matches, athletes, teams, leagues and tournaments". Every model was scored on exactly the same held-out texts, using macro-F1: the average F1 score across categories, where 1.0 is perfect.

## Where a description beats thousands of labels

On two of the three tasks, the classical models never caught up within the label budgets I tested.

{% include figure.html path="assets/img/blog/jev-vs-classical-chart.png" class="img-fluid rounded z-depth-1" alt="Learning curves of four classical models against Jev's zero-shot score on AG News, Banking77 and Emotion" %}

- **News topics (AG News).** Jev scored 0.89. The best classical model, trained on 1,000 labeled articles per topic (4,000 labels in total), reached 0.87. With 200 per topic, the best was 0.81.
- **Banking intents (Banking77).** Jev scored 0.81 across 77 intents. Logistic regression with 20 examples per intent (1,540 labels) reached 0.78.

The gaps at the top are small enough to be noise, so "matches" is the fair word. The striking part is the other end of the curves. With 10 examples per category, which is already a real labeling effort for 77 intents, the classical models sat between 0.28 and 0.69.

It was also cheap: about **$0.09 for all 1,470 Jev requests**, at roughly a quarter of a second each. That is slow next to a local model (under a millisecond), but fast enough to sit inside most workflows.

## Where it loses, and why that's interesting

On Emotion, Jev scored 0.49. The classical models passed it somewhere between 50 and 200 labeled examples per emotion, and reached about 0.8 with 500.

The easy conclusion would be "Jev is bad at emotions". Reading its most confident mistakes suggests something else:

| Text | Dataset label | Jev's answer |
| --- | --- | --- |
| "i am feeling amazing and seeing the difference" | surprise | joy |
| "…after shows i always feel a bit dazed so i hope they didnt think i was rude" | surprise | fear |
| "i feel this strange sort of liberation" | surprise | joy |
| "…i don t consider my family broken nor do i feel any discontent…" | sadness | joy |

The labels seem to follow the feeling word in the sentence (*amazing*, *dazed*, *strange* → surprise; *discontent* → sadness), not what a reader would say the author feels. A supervised model learns that word-to-label rule quickly. A model that reads for meaning disagrees with it, confidently.

So on this task, "accuracy" measures agreement with how the dataset was built. That's not a flaw of the benchmark so much as a lesson: **a model you describe the task to can only be as good as your description matches the labels you'll be judged against.** If your real categories encode a house rule, a policy or a quirk, you either write that rule into the description or you train on examples of it.

## Confidence is where things get interesting

The same model was well calibrated on two tasks and badly overconfident on the third. Calibration has a concrete meaning: across answers given about 90% probability, about 90% should be right ([Guo et al.](https://proceedings.mlr.press/v70/guo17a.html)).

| Dataset | Answers with top probability ≥ 0.9 | Correct among those | Calibration error (ECE, 0 = perfect) | True answer given 0% |
| --- | ---: | ---: | ---: | ---: |
| AG News | 88% | 93% | 0.07 | 3% |
| Banking77 | 70% | 94% | 0.08 | 6% |
| Emotion | 59% | 58% | 0.38 | 19% |

On news and banking, a simple rule works: accept Jev's answer above 0.9, and you handle 70–90% of the traffic with about 93–94% accuracy. Send the rest to a person or a stronger model. For comparison, logistic regression at its largest budget had calibration errors between 0.25 and 0.37 on these tasks.

On Emotion, the same rule fails. Half of Jev's mistakes (75 of 151) came with 90% or more probability, and in one case out of five it gave the correct label exactly zero. That's the problem I worried about before running anything: a strong preference among the options says nothing about whether the options, and their definitions, match reality. **A probability is only meaningful relative to how the labels were defined.** You can't pick a threshold because the number looks reassuring; you have to measure it on your own labeled sample, per task.

One more detail worth knowing: Jev's `confidence` field is not the probability of being right. It summarizes the shape of the distribution ([TypeSafe docs](https://docs.typesafe.ai/confidence)). All the figures above use the option probabilities.

## What changes when decisions become cheap

Think about how often we ask a language model to read something, write an answer, and then immediately reduce that answer to a category or a yes/no. Does this document matter? Which tool should handle this request? Is there enough information to continue? For those tasks the product is a decision, and the question is how cheaply and reliably we can get it.

At around a quarter of a second and a fraction of a cent per call, a decision becomes something you can put in places where you previously wouldn't have bothered. A search system could check whether it has enough evidence before fetching more. An agent could repeatedly decide whether to continue, ask for clarification or switch tools. Individually these are small judgments; across an application they change how it behaves.

My results suggest a practical rule of thumb for choosing the tool:

- **Categories you can describe well in words, or that change often** (topics, routing, intents): start with a description-based model. You get performance that would otherwise cost hundreds to thousands of labels, and you can change the categories by editing a sentence.
- **Categories defined by a house rule, a policy or a labeling convention**: labeled examples still win, because they teach the rule. A small supervised model may be exactly what you need.
- **Either way**: measure on your own labeled sample before trusting a confidence threshold, and route the uncertain cases somewhere else.

A valid output can still be a wrong answer. Constrained outputs remove a whole class of formatting problems, but choosing the right questions, supplying the right context and deciding what happens with the answer is still engineering. The architecture I find most promising splits the work: ordinary code for rules and actions, a fast decision model for bounded judgments, and a reasoning model for what needs investigation or writing. The hard part is deciding where those boundaries go.

## Before you quote these numbers

This is a small, honest experiment, not a leaderboard:

- **Pretraining overlap.** All three datasets are public and widely used, so they may be in the data Jev was trained on. That could flatter it.
- **Small test sets.** 300 to 770 texts per dataset. A 2–3 point gap (AG News, Banking77) is within noise; Jev's AG News accuracy has a 95% interval of 0.86–0.92.
- **Classical baselines are simple.** TF-IDF features only: no sentence embeddings, no fine-tuned transformers, no cheap generative LLM as a comparator. Those would close some of the gap.
- **Jev's setup wasn't tuned.** It received the same instruction on every task ("classify the primary topic"), which fits AG News better than intents or emotions. The 77 Banking77 descriptions were generated from the label names, such as "card arrival". Better wording could improve Jev's scores.
- **Balanced sampling.** Every category had the same number of examples, so this doesn't show behaviour under real-world class imbalance.
- **Harness fix.** Jev returns probabilities rounded to two decimals. My first scoring script rejected 45 answers whose probabilities summed to 0.99; the scores here were recomputed from the saved responses, with no new API calls.

Setup: `jev-1.13.0` via the TypeSafe API; 1,470 requests for about $0.09; classical models trained with scikit-learn and XGBoost on three random samples per budget, hyperparameters chosen on a separate validation set. Datasets: AG News, Banking77 (via its `mteb/banking77` copy) and Emotion, from the Hugging Face Hub.

I started this wondering how much of AI actually needs to say something. For a surprising share of everyday decisions, the answer looks like: less than we assume. The work moves into describing the decision well, and knowing when not to trust the answer.

## Sources

- [TypeSafe documentation](https://docs.typesafe.ai/introduction), [models and pricing](https://docs.typesafe.ai/models), [confidence semantics](https://docs.typesafe.ai/confidence)
- [*Jev in the Wild*: analysis of public Jev projects](https://arxiv.org/html/2609.30216v1)
- Le Scao & Rush, [How Many Data Points is a Prompt Worth?](https://aclanthology.org/2021.naacl-main.208/) (NAACL 2021)
- Guo et al., [On Calibration of Modern Neural Networks](https://proceedings.mlr.press/v70/guo17a.html)
- Zhang, Zhao & LeCun, [Character-level Convolutional Networks for Text Classification](https://arxiv.org/abs/1509.01626) (AG News)
- Casanueva et al., [Efficient Intent Detection with Dual Sentence Encoders](https://arxiv.org/abs/2003.04807) (Banking77)
- Saravia et al., [CARER: Contextualized Affect Representations for Emotion Recognition](https://aclanthology.org/D18-1404/) (Emotion)
