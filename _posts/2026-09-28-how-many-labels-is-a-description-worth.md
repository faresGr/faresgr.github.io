---
layout: post
title: "Jev vs. classical ML: how many labels is a good description worth?"
date: 2026-09-28 00:30:00+0200
description: "Following Jev’s announcement, I compared task descriptions with labeled training data on three datasets. Competitive on topics and intents, far behind on emotions: what the results say about confidence."
og_image: https://faresgr.github.io/assets/img/blog/jev-linkedin-preview.png
serve_og_meta: true
tags: [machine-learning, uncertainty, benchmarks]
categories: experiments
related_posts: false
permalink: /blog/2026/how-many-labels-is-a-description-worth/
---

On September 15, TypeSafe AI [announced Jev](https://typesafe.ai/blog/introducing-system-one-models-and-jev), its first “System One Model.” The idea caught my attention: give a model some context, define the decisions you need, and get typed answers with probabilities back. No paragraph to parse, no explanation to turn into a label. Jev gives up free-form text generation to focus on decisions that software can use directly.

I've spent a lot of time with generative models, so that trade-off is interesting to me. Think about how often we ask a language model to read something, produce an answer, and then immediately reduce that answer to a category or a boolean. A classic classifier already gives us that kind of output. The interesting question is what happens when we can define the classification task in words instead of collecting examples first.

So I tried it. **How many labeled examples does a classical classifier need before it catches up with a model you only describe the task to?** I compared Jev with logistic regression, Naive Bayes, a linear SVM and XGBoost on three public datasets. The results were encouraging on news topics and banking intents, much less so on emotions. The confidence scores made that last result particularly interesting.

## Isn't this just classification?

Partly, yes. A classifier takes an input and returns a label with a probability; we've done that for decades. The difference is how you define the task. A supervised classifier learns one mapping from labeled examples, and changing the categories usually means relabeling and retraining. With Jev, you describe the decision and the possible answers in plain language. Several questions can be asked about the same context at once ([TypeSafe documentation](https://docs.typesafe.ai/introduction)).

The promise is LLM-like flexibility behind an interface that feels like a classifier. Zero-shot classification isn't new, and neither are probabilities. My question also echoes Le Scao and Rush's [*How Many Data Points is a Prompt Worth?*](https://aclanthology.org/2021.naacl-main.208/), which measured the same trade-off for prompted fine-tuning. What deserves testing is whether this combination of flexibility, speed, cost and decision quality makes new applications practical.

## The experiment

I picked three well-known public datasets that ask very different things of a classifier:

| Dataset | Task | Categories | Test texts |
| --- | --- | ---: | ---: |
| [AG News](https://huggingface.co/datasets/fancyzhx/ag_news) | Topic of a news article | 4 | 400 |
| [Banking77](https://huggingface.co/datasets/PolyAI/banking77) | Intent of a bank customer's message | 77 | 770 |
| [Emotion](https://huggingface.co/datasets/dair-ai/emotion) | Emotion expressed in a short English post | 6 | 300 |

On one side, five classical configurations: logistic regression, Naive Bayes, a linear SVM and two XGBoost variants. All start with TF-IDF features; one XGBoost variant uses them directly, the other compresses them with truncated SVD. Each was trained on increasing amounts of labeled data, from 5 to 1,000 examples per category, repeated with three random samples. Hyperparameters were tuned on a separate validation set.

On the other side, Jev (`jev-1.13.0`), with **no task-specific training or in-context examples**. For each text it received only the category names and a one-line description of each, such as "Sports news: games, matches, athletes, teams, leagues and tournaments". Every model was scored on exactly the same held-out texts, using macro-F1: the average F1 score across categories, where 1.0 is perfect.

“Zero-shot” describes how I used Jev here, not its training history. These public datasets could overlap its pretraining. And the classical models used additional labels for validation, so the full label budget matters:

| Dataset | Training labels at largest budget, per seed | Additional validation labels |
| --- | ---: | ---: |
| AG News | 4,000 | 200 |
| Banking77 | 1,540 | 385 |
| Emotion | 3,000 | 300 |

The three training seeds draw different, potentially overlapping subsets from the same pool; these counts describe each fitted model, not three disjoint annotation budgets. Test labels are additional evaluation data, shared by both approaches.

One setup detail matters: my original Jev instruction said “classify the primary topic” for all three datasets. That is natural for news, less appropriate for intents or emotions. The category descriptions still specified the task, but this was not an optimized prompt comparison. The original results below keep that setup visible.

## How far a description gets you

On two of the three tasks, the classical models never caught up within the label budgets I tested.

{% include figure.html path="assets/img/blog/jev-vs-classical-chart.png" class="img-fluid rounded z-depth-1" alt="Learning curves of five classical configurations against Jev's original zero-shot score on AG News, Banking77 and Emotion" %}

*Classical curves show mean ± one standard deviation across three training seeds, not confidence intervals. The horizontal axis uses a real logarithmic scale. Both XGBoost variants are included; the dummy baseline is available in the repository reports. Validation labels are additional.*

- **News topics (AG News).** Jev scored 0.89. The best classical model, trained on 1,000 labeled articles per topic (4,000 labels in total), reached 0.87. With 200 per topic, the best was 0.81.
- **Banking intents (Banking77).** Jev scored 0.81 across 77 intents. Logistic regression with 20 examples per intent (1,540 labels) reached 0.78.

The gaps deserve a closer look. A paired bootstrap on the shared test texts gives a 95% interval of **−0.008 to +0.059** for Jev minus the SVM on AG News: this sample does not clearly separate them. On Banking77, the interval against logistic regression is **+0.007 to +0.060**, which supports an advantage within this experiment. These comparisons use the best observed classical configuration at the largest budget, averaged across its three fitted seeds. They do not account for selecting that configuration, new training samples or new datasets.

The other end of the curves is interesting too. With 10 examples per Banking77 intent—770 training labels, plus validation—the five classical configurations scored between 0.46 and 0.69.

It was also cheap: about **$0.094 in estimated API token charges for the original 1,470 Jev requests**, with median latency around 250–260 ms per dataset. Those estimates use $0.042 per million input tokens and no output-token charge. They exclude local compute, labeling and engineering costs. The local classifiers were much faster in this setup; Jev timings include the network, so this is a deployment comparison, not a controlled hardware comparison.

## Where it loses, and why that's interesting

On Emotion, Jev scored 0.49. The classical models passed it between the tested budgets of 50 and 200 labeled examples per emotion: 300–1,200 training labels in total, plus 300 validation labels. XGBoost on TF-IDF reached 0.82 at 500 per emotion, or 3,000 training labels.

The easy conclusion would be "Jev is bad at emotions". Looking at a few confident mistakes raised a more specific question: is it misunderstanding the text, the labeling convention, or both? These examples are illustrative, not a systematic annotation audit:

| Text | Dataset label | Jev's answer |
| --- | --- | --- |
| "i am feeling amazing and seeing the difference" | surprise | joy |
| "…after shows i always feel a bit dazed so i hope they didnt think i was rude" | surprise | fear |
| "i feel this strange sort of liberation" | surprise | joy |
| "…i don t consider my family broken nor do i feel any discontent…" | sadness | joy |

Some of these disagreements look understandable to me as a reader. That does not establish that Jev is right or that the dataset follows a simple keyword rule. Emotion labels can be ambiguous, and I have not independently relabeled the test set. The associated [CARER paper](https://aclanthology.org/D18-1404/) describes distant supervision using emotion hashtags; that is useful context, but it does not explain the provenance of every example in this particular subset.

My hypothesis is that part of the gap reflects a mismatch between the task as described and the dataset's labeling conventions. The generic “primary topic” instruction is another plausible contributor. Establishing either explanation would need controlled prompt comparisons and an annotation audit, not a handful of examples. What the scores do establish is simpler: **Jev's original setup agrees with these labels much less often than the strongest supervised baselines do.**

## Confidence is where things get interesting

Calibration was substantially better on news and banking than on Emotion, where Jev was badly overconfident. Calibration has a concrete meaning: across answers given about 90% probability, about 90% should be right ([Guo et al.](https://proceedings.mlr.press/v70/guo17a.html)).

| Dataset | Answers with top probability ≥ 0.9 | Correct among those | Calibration error (ECE, 0 = perfect) | True-label probability reported as 0.00 |
| --- | ---: | ---: | ---: | ---: |
| AG News | 88% | 93% | 0.07 | 3% |
| Banking77 | 70% | 94% | 0.08 | 6% |
| Emotion | 59% | 58% | 0.38 | 19% |

On these balanced test samples, accepting answers at a top probability of at least 0.9 would retain 70–88% of examples, with 93–94% accuracy among those retained. That is a promising starting point for a routing policy, not a production guarantee. These are descriptive test-set figures; an operational threshold needs a separate validation sample, representative class frequencies and a decision about the cost of mistakes. ECE also depends on binning and sample size, so I would not treat a single value as a certificate of calibration.

On Emotion, the same rule fails. Half of Jev's mistakes (75 of 151) came with 90% or more probability, and in one case out of five the API reported the true-label probability as 0.00. Those are finite-precision outputs, not proof that the model internally assigns exactly zero probability. That's the problem I worried about before running anything: a strong preference among the options does not establish that the choice is correct or that the task description matches the evaluation labels. **The number alone does not tell you whether to trust the decision.** You can't pick a threshold because the number looks reassuring; you have to measure it on your own labeled sample, per task.

One more detail worth knowing: Jev's `confidence` field is not the probability of being right. It summarizes the shape of the distribution ([TypeSafe docs](https://docs.typesafe.ai/confidence)). All the figures above use the option probabilities.

## What changes when decisions become cheap

Think about how often we ask a language model to read something, write an answer, and then immediately reduce that answer to a category or a yes/no. Does this document matter? Which tool should handle this request? Is there enough information to continue? For those tasks the product is a decision, and the question is how cheaply and reliably we can get it.

At around a quarter of a second and a fraction of a cent per call, a decision becomes something you can put in places where you previously wouldn't have bothered. A search system could check whether it has enough evidence before fetching more. An agent could repeatedly decide whether to continue, ask for clarification or switch tools. Individually these are small judgments; across an application they change how it behaves.

These results give me a starting point for future experiments, rather than a universal rule for choosing the tool:

- **Categories you can describe well in words, or that change often** (topics, routing, intents): a description-based model looks worth trying early. Here it was competitive with TF-IDF classifiers trained on hundreds to thousands of labels. Changing a description is easy; checking that the new decision works still needs evaluation.
- **Categories defined by a house rule, a policy or a labeling convention**: compare explicit descriptions of the rule with labeled examples. Supervised models can learn conventions from examples, but this experiment does not show that every policy task favors them.
- **Either way**: measure on your own labeled sample before trusting a confidence threshold, and route the uncertain cases somewhere else.

A valid output can still be a wrong answer. Constrained outputs remove a whole class of formatting problems, but choosing the right questions, supplying the right context and deciding what happens with the answer is still engineering. The architecture I find most promising splits the work: ordinary code for rules and actions, a fast decision model for bounded judgments, and a reasoning model for what needs investigation or writing. The hard part is deciding where those boundaries go.

## Before you quote these numbers

This is a small, honest experiment, not a leaderboard:

- **Pretraining overlap.** All three datasets are public and widely used, so they may be in the data Jev was trained on. That could flatter it.
- **Small test sets.** 300 to 770 texts per dataset. The paired intervals above resample examples within each class 5,000 times. They measure test-sample uncertainty conditional on the fitted models, not uncertainty about all possible training runs or applications.
- **Classical baselines are simple.** TF-IDF features only: no sentence embeddings, no fine-tuned transformers, no cheap generative LLM as a comparator. Those comparisons could change the picture; I have not measured them.
- **Jev's setup wasn't tuned.** It received the same instruction on every task ("classify the primary topic"), which fits AG News better than intents or emotions. The 77 Banking77 descriptions were generated from the label names, such as "card arrival". The effect of better wording needs to be measured.
- **Balanced sampling.** Every category had the same number of examples, so this doesn't show behaviour under real-world class imbalance.
- **Harness fix.** Some saved API probability distributions summed to 0.99. The initial parser rejected 45 such responses (42 Banking77, 3 Emotion). The corrected parser accepts small rounding discrepancies and normalizes the probabilities. The original scores here were recomputed from saved responses, with no new API calls; raw outputs and the original reports remain available for auditing. No original request remains a failure after rescoring.

## Code, results and what I'd test next

The [Python benchmark repository is public](https://github.com/faresGr/jev-classifier-benchmark). It includes the dataset configurations and resolved revisions, category descriptions, saved predictions, corrected reports, paired-bootstrap analysis and the script that generates these figures. You can reproduce the original score analysis without a Jev key or another API call; rerunning inference requires your own key. The [published results](https://github.com/faresGr/jev-classifier-benchmark/tree/main/published-results) preserve the original outputs alongside the corrected scores.

The next useful comparisons would be sentence-embedding classifiers, a small fine-tuned encoder and a low-cost generative model with constrained outputs. I would also test newly collected data, paraphrase the label descriptions, and deliberately include messages that fit none of the categories. A model forced to pick from a list can look confident even when the right answer is missing. Those tests would tell us more about routing and agent control than another small improvement on a familiar benchmark.

I started this wondering how much of AI actually needs to say something. For a surprising share of everyday decisions, the answer looks like: less than we assume. The work moves into describing the decision well, and knowing when not to trust the answer.

## Sources

- [TypeSafe documentation](https://docs.typesafe.ai/introduction), [models and pricing](https://docs.typesafe.ai/models), [confidence semantics](https://docs.typesafe.ai/confidence)
- [TypeSafe’s Jev announcement](https://typesafe.ai/blog/introducing-system-one-models-and-jev) (September 15, 2026)
- Le Scao & Rush, [How Many Data Points is a Prompt Worth?](https://aclanthology.org/2021.naacl-main.208/) (NAACL 2021)
- Guo et al., [On Calibration of Modern Neural Networks](https://proceedings.mlr.press/v70/guo17a.html)
- Zhang, Zhao & LeCun, [Character-level Convolutional Networks for Text Classification](https://arxiv.org/abs/1509.01626) (AG News)
- Casanueva et al., [Efficient Intent Detection with Dual Sentence Encoders](https://arxiv.org/abs/2003.04807) (Banking77)
- Saravia et al., [CARER: Contextualized Affect Representations for Emotion Recognition](https://aclanthology.org/D18-1404/) (Emotion)
