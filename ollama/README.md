# Local Qwen3.8 for OpenCode V2

Three selectable presets share the same Qwen3.8 27B Q4_K_M weights and quality
settings. Each defaults to **xhigh reasoning** and **32K output**. Only context
capacity differs; `speed` does not reduce reasoning effort or model precision.

| Preset tag under `qwen38-coding` | Context tokens | Input remainder with 32K output | Intended use |
| --- | ---: | ---: | --- |
| `speed.192k.context` | 196,608 | 163,840 | More memory headroom; selected replacement for max |
| `hight.224k.context` | 229,376 | 196,608 | More retained code/history, with observed memory pressure |
| `native.256k.context` | 262,144 | 229,376 | Model's native context ceiling; highest memory demand |

`hight` retains the requested spelling. The native name is normalized to
`native.256k.context`. Dots are supported in these installed Ollama tags. Full
OpenCode IDs begin with `ollama/qwen38-coding:` followed by the tag above.
Names describe fixed profiles, not automatic hardware sizing or measured speed
rankings. Larger context does not automatically produce better code.

**Activation status:** all three presets are configured and visible in the Desktop
picker. Former max session selections now use speed at the same 192K capacity,
with their reasoning variants retained. Existing root defaults and agent bindings
remain unchanged. No weights, cache precision or server-global settings changed.

## Reproduce

Run from the durable dotfiles checkout using compatible Ollama and OpenCode V2
installations. [Modelfile.qwen38-coding](Modelfile.qwen38-coding) owns the common
settings and 192K context. The [224K](Modelfile.qwen38-coding.224k) and
[256K](Modelfile.qwen38-coding.256k) files inherit the created speed preset and
override only `num_ctx`. Create them in this order:

```sh
rtk proxy ollama list
# Only if this exact base is absent:
rtk proxy ollama pull qwen3.8:27b-q4_K_M

# Inspect any existing target before creation; reuse equivalent definitions.
# Create only unused names or explicitly authorized updates of owned presets.
rtk proxy ollama create qwen38-coding:speed.192k.context -f ollama/Modelfile.qwen38-coding
rtk proxy ollama create qwen38-coding:hight.224k.context -f ollama/Modelfile.qwen38-coding.224k
rtk proxy ollama create qwen38-coding:native.256k.context -f ollama/Modelfile.qwen38-coding.256k

rtk proxy ollama show qwen38-coding:speed.192k.context --parameters
rtk proxy ollama show qwen38-coding:hight.224k.context --parameters
rtk proxy ollama show qwen38-coding:native.256k.context --parameters
```

Before replacing an owned preset, preserve its definition, base digest and a
recovery alias. Resolve ownership conflicts rather than overwriting unrelated
models. Do not repull or upgrade an existing base automatically.

Inheritance is a snapshot at creation. After changing common settings, recreate
speed and then both children; changing a file or recreating the parent alone does
not update existing children. All three use the same model and projector blobs,
so these definitions do not require three copies of the model weights.

Keep request overrides in all three OpenCode entries aligned with the common
Modelfile. Temperature, top_p and presence_penalty appear in the request body too;
changing only Ollama defaults does not override those explicit request values.

Merge the [OpenCode fragment](../opencode/models/qwen38-coding.json) into the
actual active JSON/JSONC file as described in the [OpenCode guide](../opencode/README.md#local-qwen38).
It is not loaded automatically. No Modelfile symlink is needed; the app-managed
live JSONC remains machine-local.

The former configured `qwen38-coding:max` entry is replaced by these three entries.
Migrate current max session selections to speed, retaining their chosen reasoning
variant. Keep historical messages unchanged. Old max, 64K, max-16k-output,
max-224k-32k and context-trial aliases remain available for recovery and may appear
through discovery, but are not the configured presets to choose for new work.

## Memory tradeoff and switching

224K keeps another 32K tokens of code and conversation available compared with
192K. It also reserves more memory. When RAM gets tight, macOS compresses memory
and moves some data to disk (swap). That can cause slower starts, pauses during
answers, and sluggishness in other apps. Severe shortages can make a request fail.
Swapping does not itself lower the configured weight or cache precision. The
benefit is more retained context, not a smarter version of the same model.

Use one large preset at a time. Ollama can queue a switch until an older loaded
model becomes idle and is unloaded. To release it immediately after its request
finishes, inspect `rtk proxy ollama ps`, then stop that specific old alias before
starting the next profile. For example, when leaving speed:

```sh
rtk proxy ollama stop qwen38-coding:speed.192k.context
```

In OpenCode's model picker select the desired named preset and xhigh. Avoid
simultaneous sessions on different large presets; installing all three definitions
does not mean their combined runtime memory fits. No global unload/concurrency
setting is changed by this setup.

Intermediate sizes are also valid `num_ctx` integers: 200K = 204800,
208K = 212992, and 216K = 221184. 208K is a reasonable midpoint trial, not a proven
sweet spot. These are suggestions, not additional installed presets. Any future
trial must update both its Ollama context and OpenCode limit, and check pressure
under the actual app workload.

## Shared settings and limits

| Setting | Value | Owner |
| --- | --- | --- |
| Base | `qwen3.8:27b-q4_K_M` | Ollama model store |
| Context | Per-preset table above | Modelfiles and OpenCode model limits |
| Output ceiling | 32,768 tokens per generation | Common Modelfile and each OpenCode output limit |
| Default effort in OpenCode | `xhigh` | Each model's `body.reasoning_effort` |
| Optional variants | low, medium, xhigh, none | Each OpenCode model entry |
| Endpoint | `http://127.0.0.1:11434/v1` | OpenCode provider settings |

Context includes input, history, reasoning and the final answer. The output
ceiling includes reasoning; it is not a separate thinking budget or session
limit. OpenCode fits output to remaining context, with additional headroom and
token estimates, so the input remainders above are arithmetic ceilings. Explicit
requests can override Ollama's `num_predict` default. Do not add a fixed
`body.max_tokens` that bypasses context fitting.

The common Modelfile retains the base template, renderer, parser and vision
components. Thinking sampling uses temperature 1.0, top_p 0.95, top_k 20,
min_p 0, presence_penalty 0 and repeat_penalty 1. None mode overrides temperature
to 0.7, top_p to 0.8 and presence_penalty to 1.5. The inherited repetition-history
window is unchanged. Raising an output ceiling does not enlarge the configured
KV cache, but can increase generation time and activity.

Reasoning is a request setting. The Modelfiles do not change other clients'
default effort. Native Ollama uses `think: "xhigh"`; this compatible route uses
`reasoning_effort: "xhigh"`. Native off is `think: false`; compatible off is
`reasoning_effort: "none"`. Do not add a Modelfile `PARAMETER think`, a thinking
budget or vLLM-specific template options. An inherited provider `body.reasoning`
can override `reasoning_effort`; inspect conflicts before merging.

## Compatibility reference

Inspected on 2026-11-05 with OpenCode Desktop/bundled CLI 2.2.5 and running
Ollama 0.40.14, on an M1 Max with 64 GiB unified memory.

Base model digest:

```text
25b843619e944cd0ae6069f94ff4e5e26a16e109ccbc0a66a0f05979ed70098e
```

The installed model reports renderer `qwen3.8`, parser `qwen3.5`, and completion,
vision, tools and thinking capabilities. Its `thinking.values` are `false`,
`low`, `medium`, `xhigh`, and its Ollama default is **medium**. A mutable tag does
not pin future weights; compare the digest when exact reproduction matters.
Software versions are compatibility references, not automatic upgrade instructions.

Before the naming change, the **192K/32K preset** passed three allocation samples spanning twenty
seconds, then a real Desktop `read` of `add.ts` and a correct answer of 5. Xhigh
was selected in the UI and both model calls; the final response stopped normally
after 4m 22s. The first call included about 18K input tokens. Ollama reported
196,608 context, 100% GPU placement and 30.25 GB allocated. All 26 pressure samples
during the tool cycle were normal, and system swap did not grow. The test model
was unloaded afterward; the configured preset loads on demand. These results
support 192K with the apps open during this check, not an automatic or permanent
hardware maximum. A nearly full 192K conversation and comparative coding quality
remain untested.

The earlier **224K/32K preset** completed a real `read` of `add.ts` and returned 5
with a normal `stop` finish through OpenCode's running backend API. Both model
calls selected max/xhigh, with reasoning content present. The cycle took 6m 40s;
the two calls contained about 16.8K and 18.2K input tokens from the existing
instruction context. Ollama reported 229,376 context, 100% GPU placement and
32.56 GB allocated. Memory pressure stayed elevated during the sampled run, and
system swap rose by up to about 1.25 GiB with other apps open. After the test,
the model was unloaded and pressure returned to normal. This verifies a small
integration cycle, not a full-window workload, comparative speed or optimal code quality. Desktop UI
interaction at 224K remains unchecked because the Mac was locked.

The earlier 256K attempt used a 16K output ceiling and loaded successfully in about 12 seconds, reporting 262,144 context
and 34.88 GB entirely in GPU memory. With the other applications open at the time,
system memory pressure rose from normal to elevated and swap usage increased by
about 3.6 GiB. The test model was unloaded; pressure returned to normal. Live
OpenCode activation was paused for a user decision on memory headroom versus
possible swapping. The user selected a 224K retry. No full-window quality claim is made.

The 224K retry also loaded entirely on GPU (32.56 GB), but elevated pressure
persisted across three samples over ten seconds after loading. It was unloaded
without activating the live OpenCode change. After unloading, about 28.6 GiB was
physically free, versus the 30.3 GiB reserved by the 224K model. These observations
describe the current application workload, not a permanent hardware limit.

The earlier **64K preset** Desktop smoke test completed a real `read` of `add.ts`
and returned 5 with Xhigh selected, finishing normally in 4m 27s. The initial
request included roughly 18K input tokens from the existing instruction context.
During that run, Ollama reported 65,536 context, 100% GPU placement and about
21 GB allocated; the system reported normal memory pressure. This is one small
integration check, not a throughput benchmark or a test of a full 64K conversation.

For the verified presets, the running OpenCode catalog retained the configured body, variants, limits and
compatibility fields. Reasoning output was observed. The outgoing HTTP body was
not captured, so exact wire-level effort and token-cap fields remain unobserved.
No image input, off-mode generation or delegated/cloud route was exercised.

The three aliases share the same weights and non-context settings. All three passed
inheritance/parameter checks, strict JSON and installed V2 parsing, native catalog
resolution, and Desktop picker visibility. Speed remained selected with Xhigh.
These checks are separate from the earlier generation evidence; no new inference
was run for this configuration change. The new 256K/32K profile has not had a full
generation or full-window quality test.

## Verify after applying

1. Inspect the base and all three aliases with `/api/show`; compare thinking metadata,
   renderer, parser, vision components and effective parameters.
2. Validate with the installed V2 parser. In the Desktop model picker, select
   `Qwen3.8 27B - speed.192k.context` and xhigh in a new disposable project/session.
3. Put `export const add = (a: number, b: number) => a + b;` in `add.ts`. Ask:
   “Use the read tool to inspect add.ts. Explain what add(2, 3) returns and why.
   Do not edit files or delegate.” Verify a real read call, result and answer 5.
4. Check `rtk proxy ollama ps` during generation for the loaded alias, actual
   context and processor placement. Check memory pressure. Confirm the request's
   alias and xhigh effort through available diagnostics without recording private
   prompts. Report unavailable request inspection separately from config validation.
5. Verify the response finishes within the cap and that existing provider,
   default-model, agent and policy settings are unchanged. Reapplying an identical
   fragment should require no rewrite.

A picker entry or HTTP success alone is insufficient. A none-mode connectivity
probe does not verify xhigh tool use. Selecting Qwen for one session does not
change model-pinned subagents or auxiliary requests; existing cloud routes remain.
Off mode prevents new thinking but does not erase historical reasoning.

## Rollback

Before merging, keep a private backup and the live file's mode, link information
and fingerprint outside Git, together with the previous model entry and migrated
session selections. Restore the backup only if the live file still matches the
recorded post-change fingerprint. If there are later unrelated edits, use a scoped
JSONC-aware merge: restore the recorded `qwen38-coding:max` entry and remove only
the three task-added entries that still match their recorded definitions. Preserve
any later edits to those entries, other models, comments and permissions; resolve
conflicts rather than overwriting them.

Restore a task-migrated session to its recorded former model and reasoning variant
only when its current selection still matches the recorded post-migration speed
selection. Leave later user selections alone. Restoring the file alone does not
reverse session selection changes. Historical messages remain unchanged.

Remove a task-created preset only when it is no longer in use and removal is
authorized. Keep the base and existing recovery aliases. Existing `setup-opencode.sh --rollback` does not undo
this manual merge. Retain private recovery records until no longer needed.

## Tuning for code quality

These are recommendations, not claims of measured code-quality improvements.

- Keep xhigh and the present thinking sampler values: they match Qwen's official
  guidance. Lowering temperature or adding a repetition penalty is not an
  evidence-backed improvement for this model. The vendor warns that increased
  presence penalties can reduce performance or cause language mixing.
- Use a 32K output ceiling, shared by reasoning and the final answer. Qwen's
  published software-engineering evaluation used `max_tokens=32768`, temperature
  1.0 and 256K context in a different agent harness. This supports 32K as a
  quality-oriented baseline, not a measured optimum for this Mac or OpenCode.
  Reserve 64K output for a later experiment if real tasks repeatedly finish at
  the length limit. Qwen's much larger separate reasoning/output recommendations
  assume other frameworks and a 1M context; do not copy them into this route.
- Keep the default f16 KV cache for precision while memory permits. Ollama's
  q8_0 cache trades some precision for roughly half the cache memory; q4_0 loses
  more precision and is a poor first choice for this quality-first preset.
  Cache quantization is server-global, so it is not changed by this Modelfile.
- Keep Flash Attention on Ollama's automatic path and avoid forcing CPU threads,
  GPU layers or parallelism without a measured need. Parallel contexts multiply
  memory requirements; validate this preset with one active request first.
- A higher-precision weight build is a separate quality experiment. The official
  `qwen3.8:27b-q8_0` download is about 30 GB versus about 18 GB for this Q4_K_M
  base. It may reduce quantization error, but no comparative coding benefit or
  fit alongside the chosen large context has been established here. Do not download or switch
  weights automatically.
- More context allows more relevant code to remain available. It does not itself
  establish better answers: keep retrieval focused and assess changes with real
  repository tasks and tests. This small integration test is not a code-quality
  benchmark or a full-context retrieval test.

| Parameter | Selected value | Reason for this machine and quality goal |
| --- | --- | --- |
| Context / output | 192K, 224K or 256K / 32K | Select memory headroom versus retained history; speed stays at the passing 192K size |
| Reasoning effort | xhigh | Official recommendation for complex tasks; already configured before this review |
| Temperature / top_p | 1.0 / 0.95 | Published thinking-mode defaults; no evidence lower values improve coding here |
| top_k / min_p | 20 / 0 | Published thinking-mode defaults, retained in Ollama |
| Presence / repetition penalties | 0 / 1 | Avoid unsupported changes to the published sampling recipe |
| KV cache | Default f16 | Preserve cache precision; attention-cache estimates are 12, 14 and 16 GiB for the three sizes |
| Weight quantization | Q4_K_M | Existing tested base; Q8 plus this large context has unproven fit and coding benefit here |
| Flash Attention | Automatic | Use Ollama's supported backend selection without a global override |
| Parallel requests | Default 1 | Avoid multiplying this large context's memory allocation |
| Threads, GPU layers, batch, seed | Inherited/default | No local evidence supports overriding backend choices or fixing a seed |

These cache estimates use 16 full-attention layers, 4 KV heads, head dimension
256, K and V, and two bytes per element. It excludes weights, recurrent state,
vision components, buffers and other apps. Actual loaded-model allocation is the
more useful fit check. Q8 weights and Q8 KV cache are different changes; neither
was applied. Optional none-mode sampling stays 0.7 / 0.8 / 1.5 for temperature,
top_p and presence penalty; xhigh remains the coding default.

## Sources

- [Apple memory pressure, compression and swap](https://support.apple.com/guide/activity-monitor/view-memory-usage-actmntr1004/mac)

- [OpenCode V2 configuration](https://opencode.ai/v2/docs/config/)
- [OpenCode V2 models, variants and compatibility](https://opencode.ai/v2/docs/models/)
- [OpenCode V2 providers](https://opencode.ai/v2/docs/providers/)
- [Exact Ollama model tag](https://ollama.com/library/qwen3.8:27b-q4_K_M)
- [Ollama Modelfile reference](https://docs.ollama.com/modelfile)
- [Ollama context allocation](https://docs.ollama.com/context-length)
- [Ollama Flash Attention, KV cache and concurrency](https://docs.ollama.com/faq)
- [Optional Q8_0 weight build](https://ollama.com/library/qwen3.8:27b-q8_0)
- [Ollama thinking metadata](https://docs.ollama.com/capabilities/thinking)
- [Ollama OpenAI compatibility](https://docs.ollama.com/api/openai-compatibility)
- [Qwen official model card and sampling guidance](https://huggingface.co/Qwen/Qwen3.8-27B)
- [Qwen architecture configuration](https://huggingface.co/Qwen/Qwen3.8-27B/blob/main/config.json)
- [OpenCode output fitting source](https://github.com/anomalyco/opencode/blob/9bbb8ce18c80f099e0e448775f59d965ead40a21/packages/core/src/session/model-request.ts)
