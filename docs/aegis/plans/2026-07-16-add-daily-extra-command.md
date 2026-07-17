# /daily_extra Implementation Plan

## Goal

Implement the approved manual /daily_extra command for Sheep and 0x3f daily sources, preserving ordered multi-problem envelopes, showing an overview before details, and keeping every selected detail ephemeral.

## Architecture

Keep the existing owners and compose them:

- OjApiClient owns upstream request parameters and response envelopes.
- get_daily_payload() owns process-local daily payload coalescing and cache identity.
- ui_helpers owns source-aware problem cards, overview embeds, and safe persistent problem-detail buttons.
- SlashCommandsCog owns slash-command validation, visibility, orchestration, and error mapping.
- InteractionHandlerCog remains unchanged and owns stateless problem view clicks through problem|source|id|view.

The new command uses a source-only API method, while existing LeetCode callers keep get_daily(domain, date) and oj-api-rs v0.4 normalization. The payload cache uses explicit target namespaces so domains and additional sources cannot collide.

## Tech Stack

- Python 3.10+
- discord.py 2.5+
- aiohttp
- pytest, pytest-asyncio, unittest.mock
- Ruff
- OpenSpec spec-driven workflow

## Baseline / Authority Refs

- openspec/changes/add-daily-extra-command/proposal.md
- openspec/changes/add-daily-extra-command/design.md
- openspec/changes/add-daily-extra-command/specs/daily-extra-command/spec.md
- openspec/changes/add-daily-extra-command/specs/daily-request-deduplication/spec.md
- openspec/specs/interaction-handler/spec.md
- openspec/specs/discord-ui/spec.md
- openspec/specs/command-localization/spec.md
- openspec/specs/locale-files/spec.md
- /home/usaya/workspace/github/oj-api-rs/openspec/specs/daily-challenge/spec.md at dev commit 4536487

## Compatibility Boundary

- Preserve OjApiClient.get_daily(domain="com", date=None).
- Preserve v0.4 flat LeetCode daily normalization and its informational log.
- Preserve /daily, /daily_cn, LeetCode historical lookup, and scheduled delivery.
- Preserve the problem|source|id|view format and existing ephemeral view handler.
- Do not add configuration fields, database schema, migrations, scheduled jobs, dependencies, or additional source values.
- /daily_extra requires the newer oj-api-rs source query contract; a v0.4 backend may return the existing localized generic API error for this command only.

## Verification

Run from the repository root:

    .venv/bin/pytest -o addopts='' -o cache_dir=/tmp/leetcode-daily-discord-bot-pytest-cache -q \
      tests/test_daily_payload_reuse.py \
      tests/test_daily_extra_command.py \
      tests/test_slash_problem_command.py \
      tests/test_interaction_handler.py \
      tests/test_history_dates.py

    uv run --extra dev ruff check .
    uv run --extra dev pytest -o cache_dir=/tmp/leetcode-daily-discord-bot-pytest-cache
    openspec validate add-daily-extra-command --strict --no-interactive
    python3 /home/usaya/.codex/aegis/scripts/aegis-workspace.py check --root .
    git diff --check

Expected result: all focused and full tests pass, Ruff reports no errors, the OpenSpec change is valid, the Aegis workspace check passes, and git diff has no whitespace errors.

## Aegis Visibility

Planning is necessary because this public slash command crosses the API contract, cache identity, Discord interaction safety, localization, and compatibility boundaries; pinning owners and tests first prevents a caller-side source hack or a second interaction protocol.

## Plan Basis

- Approved behavior: dedicated manual /daily_extra; source choices Sheep and 0x3f; optional date/public; one problem opens directly; multiple problems show an overview; selected details are always private.
- TDD Route: light. The user requested concrete test cases, so each new contract receives focused tests before its source edit, without imposing strict micro-commit TDD on unchanged compatibility surfaces.
- ArchitectureReviewRequired: yes, because this is a public command and cross-module API/cache/UI contract change.

## BaselineUsageDraft

- Required baseline refs: approved OpenSpec change, existing interaction/UI/localization specs, upstream daily challenge contract.
- Delivered context refs: current api_client.py, ui_helpers.py, slash_commands_cog.py, interaction_handler_cog.py, locale files, and focused tests.
- Acknowledged before plan refs: all required refs above.
- Cited in plan refs: all required refs above.
- Missing refs: none.
- Decision: continue.

## Requirement Ready Check

- Requirement source refs: approved conversation design and OpenSpec change add-daily-extra-command.
- Goals and scope refs: proposal Why, What Changes, and design Goals / Non-Goals.
- User / scenario refs: daily-extra-command spec scenarios.
- Requirement item refs: six added daily-extra requirements and modified in-flight payload reuse.
- Acceptance / verification criteria refs: OpenSpec scenarios, PBT properties, and this plan's verification section.
- Open blocker questions: none.
- Decision: ready.

## Ripple Signal Triage

- Producer: OjApiClient daily request methods.
- Shared transformation: get_daily_payload() and its cache/in-flight keys.
- Consumers: /daily, /daily_cn, send_daily_challenge(), scheduled delivery, and new /daily_extra.
- UI/interaction: generic problem overview and unchanged unified view handler.
- Localization: three locale JSON files and command translator lookup.
- Verification expansion: focused extra-source tests plus existing LeetCode daily, history, interaction, and full-suite regression.
- Decision: expand verification across producer, shared payload, all daily consumers, UI, and i18n.

## Change Necessity

- User-visible need: manually query Sheep or 0x3f daily data and safely inspect multiple returned problems.
- No-change / non-code option: documentation alone cannot register the command, send source parameters, preserve all problems, or control Discord response visibility.
- Why code change is necessary: existing public methods accept only LeetCode domains and downstream daily rendering selects problems[0].
- Minimum change boundary: api_client.py, ui_helpers.py, slash_commands_cog.py, ui_constants.py, locale files, README, and focused tests.
- Decision: code-change.

## Existence Check

### New slash command

- Proposed new surface: /daily_extra.
- Existing owner / reuse candidate: /daily and /daily_cn.
- Why existing surface is insufficient: their domain semantics and scheduled LeetCode behavior are stable compatibility boundaries; overloading them would change accepted behavior.
- Creation proof: the user approved a dedicated manual command with two explicit source choices.
- Entropy / retirement impact: one public command; no replacement or retirement.
- Decision: add-with-proof.

### Additional-source API method

- Proposed new surface: OjApiClient.get_daily_by_source().
- Existing owner / reuse candidate: OjApiClient.get_daily(domain, date).
- Why existing surface is insufficient: its default domain and v0.4 normalization contract make source/domain conflicts easy to introduce.
- Creation proof: the upstream endpoint has a distinct source query contract unavailable in v0.4.
- Entropy / retirement impact: a small sibling method; reuse the existing HTTP layer; no fallback.
- Decision: add-with-proof.

### Discord interaction protocol

- Proposed new surface: daily-specific view/custom id.
- Existing owner / reuse candidate: problem|source|id|view and InteractionHandlerCog.
- Why existing surface is insufficient: it is sufficient.
- Creation proof: none.
- Entropy / retirement impact: no new state or router.
- Decision: reuse-existing.

### Test owner

- Proposed new surface: tests/test_daily_extra_command.py.
- Existing owner / reuse candidate: test_slash_problem_command.py and test_daily_payload_reuse.py.
- Why existing surface is insufficient: the existing slash test file is already broad, while the new file can cohesively own command/UI scenarios; payload contract tests remain in the existing payload file.
- Creation proof: the feature has a distinct public command and a multi-scenario acceptance matrix.
- Entropy / retirement impact: one cohesive test file; remove it if the command is retired.
- Decision: add-with-proof.

## Architecture Integrity Lens

- Invariant: daily payload identity is target kind + target value + date.
- Canonical owners: API parameters in OjApiClient; cache identity in get_daily_payload(); Discord button safety in ui_helpers; command orchestration in SlashCommandsCog; click privacy in InteractionHandlerCog.
- Responsibility overlap: avoid validating source query details in the command and avoid rebuilding custom ids outside ui_helpers.
- Higher-level simplification: preserve one payload cache and one unified problem-detail route.
- Retirement / falsifier: if implementation adds a daily-specific interaction handler, a second payload cache, or scheduler/config edits, it has drifted from the approved design.
- Verdict: aligned.

## Plan Pressure Test

- Owner / contract / retirement: each change has one current owner; no old path is replaced.
- Architecture integrity / higher-level path: shared payload and shared view safety are changed at their canonical owners.
- Verification scope: producer, cache, command, UI, interaction privacy, localization, docs, and existing daily regressions are covered.
- Task executability: every task names exact files, tests, commands, and commit boundary.
- Pressure result: proceed.

## Complexity Budget

- Artifact class: source and maintained test code.
- Target files / artifacts: ui_helpers.py (1165 lines), slash_commands_cog.py (694), api_client.py (312), test_daily_payload_reuse.py (325), new focused test file.
- Current pressure: ui_helpers.py is near the 1200-line strong pressure threshold and already owns several UI responsibilities.
- Projected post-change pressure: small owner-local safety/footer edits keep ui_helpers.py near but below/around the threshold; command tests go to a new cohesive file instead of enlarging a broad existing file.
- Budget result: at-risk.
- Planned governance: ui_helpers receives only owner-local extraction/reuse; no new view class or daily service is added. If implementation would push a cohesive touched block beyond roughly 80 lines, pause and extract the generic detail-view safety helper rather than adding command-specific checks.

## Plan-Time Complexity Check

- Target files: ui_helpers.py, slash_commands_cog.py, api_client.py, tests.
- Existing size / shape signals: ui_helpers.py is large; slash_commands_cog.py is moderately large; API client is compact.
- Owner fit: all proposed edits match current owners.
- Add-in-place risk: command-specific UI validation in SlashCommandsCog would duplicate button safety and worsen coupling.
- Better file boundary: generic all-or-nothing safety remains in ui_helpers; command tests use a new dedicated test file.
- Recommendation: edit existing owners, add one focused test file, and do not add a production module.

## Execution Readiness View

- Intent Lock: manual /daily_extra only.
- Scope Fence: no scheduler, DB, configuration, pagination, message editing, or new sources.
- Baseline Lock: OpenSpec add-daily-extra-command plus existing interaction/UI/localization contracts.
- Approved Behavior: single direct card, multiple ordered overview, public flag only for initial response, private selected details.
- Owner / Contract Constraints: preserve get_daily() and unified problem custom ids.
- Compatibility Boundary: existing LeetCode and v0.4 paths remain stable.
- Retirement Boundary: no old owner retires; no fallback is added.
- Task Batches: API/payload, UI safety, command/i18n, privacy/docs/verification.
- Test Obligations: focused RED/GREEN tests, existing daily regressions, full suite, Ruff, OpenSpec.
- Review Gates: review API parameter shape after Task 1 and public/private behavior after Task 3.
- Drift / Rewind Rules: stop and return to design if implementation needs scheduler state, a new custom id, or a second cache.
- Evidence Required Before Completion: exact command outputs, OpenSpec validity, locale parity, clean diff check, and architecture review.
- Advisory Boundary: method-pack execution guidance only; not GateDecision, PolicySnapshot, or completion authority.

## File Map

Create:

- tests/test_daily_extra_command.py: command, overview safety, and locale parity acceptance tests.

Modify:

- src/bot/api_client.py: add source-only daily method.
- src/bot/utils/ui_helpers.py: preserve all daily problems, namespace cache targets, skip extra-source history, enforce complete safe overview views, support footer override.
- src/bot/utils/ui_constants.py: canonical display labels for Sheep and 0x3f.
- src/bot/cogs/slash_commands_cog.py: register and orchestrate /daily_extra.
- src/bot/i18n/locales/zh-TW.json: source-of-truth command/runtime strings.
- src/bot/i18n/locales/en-US.json: English parity.
- src/bot/i18n/locales/zh-CN.json: Simplified Chinese parity.
- tests/test_daily_payload_reuse.py: API and shared payload contract tests.
- tests/test_interaction_handler.py: private detail characterization assertion.
- README.md: public command usage.

Do not modify:

- src/bot/cogs/interaction_handler_cog.py
- src/bot/cogs/schedule_manager_cog.py
- database schema or migrations
- configuration models or config.toml

## Task 1: Add the source-only API method and target-aware daily payload

Files:

- Modify: src/bot/api_client.py
- Modify: src/bot/utils/ui_helpers.py
- Modify: tests/test_daily_payload_reuse.py

Why:

The command cannot safely use the domain-only client method, and the shared payload must retain every returned problem while preventing source/date cache collisions.

Change Necessity:

The source query and complete envelope do not exist in the current client/payload contracts. The minimum boundary is one sibling API method plus the existing payload/cache owner.

Impact / Compatibility:

Existing get_daily() callers remain unchanged. Existing payload keys challenge_info, history_problems, and resolved_date remain available; problems and daily_source are additive. LeetCode history behavior remains active only for domain targets.

Verification:

    .venv/bin/pytest -o addopts='' -o cache_dir=/tmp/leetcode-daily-discord-bot-pytest-cache -q tests/test_daily_payload_reuse.py

- [ ] 1.1 Write the failing API and payload tests.

  In tests/test_daily_payload_reuse.py, extend _make_bot() so bot.api contains both methods:

        bot.api = SimpleNamespace(
            get_daily=AsyncMock(return_value=_daily_response()),
            get_daily_by_source=AsyncMock(),
        )

  Add this helper and these tests:

        def _extra_daily_response(source: str = "sheep", date: str = "2026-06-02") -> dict:
            return {
                "date": date,
                "source": source,
                "problems": [
                    {
                        "id": "100A",
                        "source": "codeforces",
                        "slug": "100A",
                        "title": "First",
                        "difficulty": None,
                        "ac_rate": None,
                        "rating": 1200,
                        "tags": ["implementation"],
                        "link": "https://codeforces.com/problemset/problem/100/A",
                    },
                    {
                        "id": "200B",
                        "source": "codeforces",
                        "slug": "200B",
                        "title": "Second",
                        "difficulty": None,
                        "ac_rate": None,
                        "rating": 1400,
                        "tags": ["math"],
                        "link": "https://codeforces.com/problemset/problem/200/B",
                    },
                ],
            }


        @pytest.mark.asyncio
        async def test_get_daily_by_source_sends_source_without_domain():
            response = _extra_daily_response("sheep", "2026-06-02")
            api = OjApiClient("http://test")
            api._session = AsyncMock()
            api._request = AsyncMock(return_value=response)

            result = await api.get_daily_by_source("sheep", "2026-06-02")

            assert result is response
            api._request.assert_awaited_once_with(
                "GET",
                "daily",
                params={"source": "sheep", "date": "2026-06-02"},
            )


        @pytest.mark.asyncio
        async def test_extra_daily_payload_preserves_order_and_skips_history(monkeypatch):
            bot = _make_bot()
            response = _extra_daily_response()
            bot.api.get_daily_by_source.return_value = response
            history = AsyncMock()
            monkeypatch.setattr(ui_helpers, "_fetch_daily_history", history)

            payload = await get_daily_payload(
                bot,
                date_str="2026-06-02",
                source="sheep",
            )

            assert [problem["id"] for problem in payload["problems"]] == ["100A", "200B"]
            assert payload["challenge_info"]["id"] == "100A"
            assert payload["daily_source"] == "sheep"
            assert payload["resolved_date"] == "2026-06-02"
            assert payload["history_problems"] == []
            history.assert_not_awaited()
            bot.api.get_daily_by_source.assert_awaited_once_with("sheep", "2026-06-02")


        @pytest.mark.asyncio
        async def test_daily_payload_cache_isolated_by_target(monkeypatch):
            bot = _make_bot()
            monkeypatch.setattr(ui_helpers, "generate_history_dates", lambda anchor_date: [])
            bot.api.get_daily_by_source.side_effect = [
                _extra_daily_response("sheep"),
                _extra_daily_response("0x3f"),
            ]

            leetcode = await get_daily_payload(bot, "com", "2026-06-02")
            sheep = await get_daily_payload(bot, date_str="2026-06-02", source="sheep")
            zero_x3f = await get_daily_payload(bot, date_str="2026-06-02", source="0x3f")
            sheep_again = await get_daily_payload(bot, date_str="2026-06-02", source="sheep")

            assert leetcode["daily_source"] == "leetcode.com"
            assert sheep["daily_source"] == "sheep"
            assert zero_x3f["daily_source"] == "0x3f"
            assert sheep_again is sheep
            assert bot.api.get_daily.await_count == 1
            assert bot.api.get_daily_by_source.await_count == 2
            assert ("domain:com", "2026-06-02") in bot._daily_payload_cache
            assert ("source:sheep", "2026-06-02") in bot._daily_payload_cache
            assert ("source:0x3f", "2026-06-02") in bot._daily_payload_cache


        @pytest.mark.asyncio
        async def test_extra_daily_payload_coalesces_identical_in_flight_requests():
            bot = _make_bot()
            started = asyncio.Event()
            release = asyncio.Event()
            calls = 0

            async def fetch(source, date=None):
                nonlocal calls
                calls += 1
                started.set()
                await release.wait()
                return _extra_daily_response(source, date or "2026-06-02")

            bot.api.get_daily_by_source.side_effect = fetch
            first = asyncio.create_task(
                get_daily_payload(bot, date_str="2026-06-02", source="sheep")
            )
            await started.wait()
            second = asyncio.create_task(
                get_daily_payload(bot, date_str="2026-06-02", source="sheep")
            )
            release.set()

            first_payload, second_payload = await asyncio.gather(first, second)

            assert first_payload is second_payload
            assert calls == 1

- [ ] 1.2 Verify RED.

  Run:

        .venv/bin/pytest -o addopts='' -o cache_dir=/tmp/leetcode-daily-discord-bot-pytest-cache -q tests/test_daily_payload_reuse.py

  Expected failures before implementation:

  - OjApiClient has no get_daily_by_source attribute.
  - get_daily_payload() rejects the source keyword.
  - payloads have no problems or daily_source keys.
  - cache keys are not target-namespaced.

- [ ] 1.3 Implement the minimum API and payload changes.

  Add this sibling method after get_daily() in src/bot/api_client.py:

        async def get_daily_by_source(self, source: str, date: str | None = None) -> dict | None:
            params = {"source": source}
            if date:
                params["date"] = date
            return await self._request("GET", "daily", params=params)

  In src/bot/utils/ui_helpers.py, add a complete-envelope extractor and keep the primary helper as a compatibility projection:

        def _get_daily_problems(response: dict[str, Any] | None) -> list[dict[str, Any]] | None:
            if not response:
                return None
            problems = response.get("problems")
            if (
                not isinstance(problems, list)
                or not problems
                or not all(isinstance(problem, dict) for problem in problems)
            ):
                return None

            resolved = [dict(problem) for problem in problems]
            if response.get("date"):
                for problem in resolved:
                    problem["date"] = response["date"]
            return resolved


        def _get_primary_daily_problem(response: dict[str, Any] | None) -> dict[str, Any] | None:
            problems = _get_daily_problems(response)
            return problems[0] if problems else None

  Replace _fetch_daily_payload() with:

        async def _fetch_daily_payload(
            bot: Any,
            domain: str,
            date_str: str | None,
            fallback_date: str,
            *,
            source: str | None = None,
        ) -> dict[str, Any] | None:
            if source is not None:
                daily_response = await bot.api.get_daily_by_source(source, date_str)
            elif date_str:
                daily_response = await bot.api.get_daily(domain, date_str)
            else:
                daily_response = await bot.api.get_daily(domain)

            problems = _get_daily_problems(daily_response)
            if not problems:
                return None

            resolved_date = daily_response.get("date") or date_str or fallback_date
            history_problems = (
                [] if source is not None else await _fetch_daily_history(bot, domain, resolved_date)
            )
            return {
                "challenge_info": problems[0],
                "problems": problems,
                "history_problems": history_problems,
                "resolved_date": resolved_date,
                "daily_source": daily_response.get("source")
                or source
                or ("leetcode.cn" if domain == "cn" else "leetcode.com"),
            }

  Change get_daily_payload() to accept source as a keyword-only target and use a namespaced key:

        async def get_daily_payload(
            bot: Any,
            domain: str = "com",
            date_str: str | None = None,
            *,
            source: str | None = None,
        ) -> dict[str, Any] | None:
            fallback_timezone = pytz.timezone("Asia/Taipei") if source is not None else pytz.UTC
            fallback_date = datetime.now(fallback_timezone).strftime("%Y-%m-%d")
            target_key = f"source:{source}" if source is not None else f"domain:{domain}"
            cache_key = (target_key, date_str or f"{_CURRENT_DAILY_PAYLOAD_KEY}:{fallback_date}")
            cache, in_flight, lock = _get_daily_payload_state(bot)

  Preserve the existing function body, but make these exact substitutions:

        return await _fetch_daily_payload(
            bot,
            domain,
            date_str,
            fallback_date,
            source=source,
        )

        cache[(target_key, actual_date)] = (inserted_at, payload)

  Update the three existing cache/in-flight fixtures and assertions in tests/test_daily_payload_reuse.py exactly:

        bot._daily_payload_in_flight = {
            ("domain:com", "2026-06-03"): failed_task
        }

        bot._daily_payload_cache = {
            ("domain:com", "2026-06-01"): (0.0, old_payload)
        }

        assert ("domain:com", "2026-06-01") not in bot._daily_payload_cache
        assert ("domain:com", "2026-06-03") in bot._daily_payload_cache

  Keep the parametrized ("com", "leetcode.com") API-domain test data unchanged; those values are API inputs, not cache keys.

- [ ] 1.4 Verify GREEN and compatibility.

  Run:

        .venv/bin/pytest -o addopts='' -o cache_dir=/tmp/leetcode-daily-discord-bot-pytest-cache -q \
          tests/test_daily_payload_reuse.py tests/test_history_dates.py tests/test_schedule_manager_cog.py

  Expected: all tests pass; existing get_daily() request assertions remain unchanged.

- [ ] 1.5 Commit the API/payload slice.

  Review git diff for only the files in this task, then:

        git add src/bot/api_client.py src/bot/utils/ui_helpers.py tests/test_daily_payload_reuse.py
        git commit -m "✨ feat(api): support additional daily payloads"

## Task 2: Make overview detail buttons complete and safe

Files:

- Modify: src/bot/utils/ui_helpers.py
- Create: tests/test_daily_extra_command.py
- Regression: tests/test_similar_results.py
- Regression: tests/test_slash_problem_command.py

Why:

The existing overview view silently slices to 25 items and does not validate routing segments. /daily_extra must either expose every returned problem safely or reject the payload without a partial view.

Change Necessity:

Command-side validation would duplicate Discord custom-id ownership. The minimum stable change is a generic safety predicate in ui_helpers plus an optional overview footer.

Impact / Compatibility:

Existing /problem requests are capped at 20 and continue to receive a view for valid resolved problems. Similar-result behavior reuses the same safety primitive and must retain its all-or-nothing behavior.

Verification:

    .venv/bin/pytest -o addopts='' -o cache_dir=/tmp/leetcode-daily-discord-bot-pytest-cache -q \
      tests/test_daily_extra_command.py tests/test_similar_results.py tests/test_slash_problem_command.py

- [ ] 2.1 Write the failing overview safety tests.

  Create tests/test_daily_extra_command.py with:

        import discord

        from bot.utils.ui_helpers import (
            create_problems_overview_embed,
            create_problems_overview_view,
        )


        def _problem(problem_id: str, *, source: str = "codeforces") -> dict:
            return {
                "id": problem_id,
                "source": source,
                "slug": problem_id,
                "title": f"Problem {problem_id}",
                "difficulty": None,
                "ac_rate": None,
                "rating": 1200,
                "tags": ["implementation"],
                "link": f"https://example.com/{problem_id}",
            }


        def test_daily_overview_view_preserves_exact_25_problem_order():
            problems = [_problem(str(index)) for index in range(1, 26)]

            view = create_problems_overview_view(problems, "com")

            assert view is not None
            assert [button.label for button in view.children] == [
                str(index) for index in range(1, 26)
            ]
            assert [button.row for button in view.children[:6]] == [0, 0, 0, 0, 0, 1]
            assert view.children[-1].row == 4


        def test_daily_overview_view_rejects_more_than_25_problems():
            problems = [_problem(str(index)) for index in range(1, 27)]

            assert create_problems_overview_view(problems, "com") is None


        def test_daily_overview_view_rejects_unsafe_routing_fields():
            problems = [_problem("100A"), _problem("bad|id")]

            assert create_problems_overview_view(problems, "com") is None


        def test_daily_overview_embed_accepts_daily_footer_override():
            problems = [_problem("100A"), _problem("200B")]

            embed = create_problems_overview_embed(
                problems,
                "com",
                title="Sheep Daily | 2026-06-02",
                source_label="Sheep",
                footer_icon_url=None,
                footer_text="Sheep Daily | 2026-06-02",
            )

            assert isinstance(embed, discord.Embed)
            assert embed.title == "Sheep Daily | 2026-06-02"
            assert embed.footer.text == "Sheep Daily | 2026-06-02"

- [ ] 2.2 Verify RED.

  Run:

        .venv/bin/pytest -o addopts='' -o cache_dir=/tmp/leetcode-daily-discord-bot-pytest-cache -q tests/test_daily_extra_command.py

  Expected failures:

  - 26 problems currently produce a partial 25-button view.
  - unsafe segments are accepted.
  - create_problems_overview_embed() does not accept footer_text.

- [ ] 2.3 Implement shared all-or-nothing safety and footer override.

  Add this generic predicate near _can_create_similar_result_view() in src/bot/utils/ui_helpers.py:

        def _can_create_problem_detail_view(
            problems: List[Dict[str, Any]],
            *,
            max_items: int,
            was_truncated: bool = False,
        ) -> bool:
            return (
                bool(problems)
                and not was_truncated
                and len(problems) <= max_items
                and all(
                    isinstance(problem, dict)
                    and _is_safe_problem_button_segment(problem.get("source"))
                    and _is_safe_problem_button_segment(
                        problem.get("id"),
                        max_length=MAX_BUTTON_LABEL_LENGTH,
                    )
                    and len(
                        _build_problem_custom_id(
                            problem.get("source"),
                            problem.get("id"),
                            "view",
                        )
                    )
                    <= MAX_BUTTON_CUSTOM_ID_LENGTH
                    for problem in problems
                )
            )

  Replace _can_create_similar_result_view() with a delegation:

        def _can_create_similar_result_view(
            results: List[Dict[str, Any]],
            *,
            was_truncated: bool,
        ) -> bool:
            return _can_create_problem_detail_view(
                results,
                max_items=MAX_SIMILAR_RESULT_DETAIL_BUTTONS,
                was_truncated=was_truncated,
            )

  Change create_problems_overview_view() to return no partial view:

        def create_problems_overview_view(
            problems: List[Dict[str, Any]],
            domain: str,
        ) -> discord.ui.View | None:
            if not _can_create_problem_detail_view(
                problems,
                max_items=MAX_PROBLEMS_PER_OVERVIEW,
            ):
                return None

            view = discord.ui.View()
            for index, problem in enumerate(problems):
                emoji = get_problem_emoji(problem)
                source, problem_id = _normalize_problem_button_segments(
                    problem["source"],
                    problem["id"],
                )
                view.add_item(
                    discord.ui.Button(
                        style=discord.ButtonStyle.secondary,
                        label=problem_id,
                        emoji=emoji,
                        custom_id=_build_problem_custom_id(source, problem_id, "view"),
                        row=index // 5,
                    )
                )
            return view

  Add footer_text after locale in the create_problems_overview_embed() signature so all existing positional parameters remain stable:

        locale: str = "zh-TW",
        footer_text: Optional[str] = None,

  Resolve the footer with:

        resolved_footer_text = footer_text or (
            i18n.t("ui.embed.problems_overview", locale, source_label=source_label)
            if i18n
            else f"📋 {source_label} Problems Overview"
        )

  Use resolved_footer_text in both set_footer() branches.

- [ ] 2.4 Verify GREEN and existing overview consumers.

  Run:

        .venv/bin/pytest -o addopts='' -o cache_dir=/tmp/leetcode-daily-discord-bot-pytest-cache -q \
          tests/test_daily_extra_command.py tests/test_similar_results.py tests/test_similar_cog.py \
          tests/test_slash_problem_command.py

  Expected: new safety tests pass; existing /problem and similar-result tests remain green.

- [ ] 2.5 Commit the UI safety slice.

        git add src/bot/utils/ui_helpers.py tests/test_daily_extra_command.py
        git commit -m "🐛 fix(ui): prevent partial problem overviews"

## Task 3: Register /daily_extra and localize its responses

Files:

- Modify: src/bot/cogs/slash_commands_cog.py
- Modify: src/bot/utils/ui_constants.py
- Modify: src/bot/i18n/locales/zh-TW.json
- Modify: src/bot/i18n/locales/en-US.json
- Modify: src/bot/i18n/locales/zh-CN.json
- Modify: tests/test_daily_extra_command.py

Why:

This is the requested public entry point and must compose the approved API/payload/UI contracts while keeping initial visibility separate from detail visibility.

Change Necessity:

No existing command accepts additional daily sources. The minimum boundary is one command callback plus labels and locale keys; the interaction handler remains unchanged.

Impact / Compatibility:

The command is additive. /daily and /daily_cn signatures and behavior do not change. public controls only the initial response.

Verification:

    .venv/bin/pytest -o addopts='' -o cache_dir=/tmp/leetcode-daily-discord-bot-pytest-cache -q \
      tests/test_daily_extra_command.py tests/test_slash_problem_command.py

- [ ] 3.1 Add command, visibility, rendering, validation, and error tests.

  Extend imports in tests/test_daily_extra_command.py:

        import json
        from pathlib import Path
        from types import SimpleNamespace
        from unittest.mock import AsyncMock, MagicMock, sentinel

        import pytest
        from discord.ext import commands

        from bot.api_client import (
            ApiError,
            ApiNetworkError,
            ApiProcessingError,
            ApiRateLimitError,
        )
        from bot.cogs import slash_commands_cog as slash_commands_module
        from bot.cogs.slash_commands_cog import SlashCommandsCog

  Add these helpers:

        def _make_bot():
            bot = MagicMock(spec=commands.Bot)
            bot.api = AsyncMock()
            bot.llm = MagicMock()
            bot.llm_pro = MagicMock()
            bot.config = SimpleNamespace(default_locale="zh-TW")
            bot.i18n = MagicMock()
            bot.i18n.resolve_locale = MagicMock(return_value="zh-TW")
            bot.i18n.t = MagicMock(
                side_effect=lambda key, locale, **kwargs: key.format(**kwargs)
            )
            return bot


        def _make_interaction():
            interaction = AsyncMock(spec=discord.Interaction)
            interaction.response = AsyncMock()
            interaction.response.defer = AsyncMock()
            interaction.followup = AsyncMock()
            interaction.followup.send = AsyncMock()
            interaction.user = MagicMock(name="tester", display_name="tester")
            interaction.user.name = "tester"
            interaction.guild = MagicMock(id=123)
            interaction.guild_locale = None
            interaction.locale = discord.Locale.taiwan_chinese
            return interaction


        def _payload(source: str, problems: list[dict]) -> dict:
            return {
                "challenge_info": problems[0],
                "problems": problems,
                "history_problems": [],
                "resolved_date": "2026-06-02",
                "daily_source": source,
            }

  Add these tests:

        def test_daily_extra_source_choices_are_exact():
            source_parameter = next(
                parameter
                for parameter in SlashCommandsCog.daily_extra_command.parameters
                if parameter.name == "source"
            )

            assert [(choice.name, choice.value) for choice in source_parameter.choices] == [
                ("Sheep", "sheep"),
                ("0x3f", "0x3f"),
            ]


        @pytest.mark.asyncio
        @pytest.mark.parametrize(
            ("source", "date", "public"),
            [
                ("sheep", None, False),
                ("0x3f", "2026-06-02", True),
            ],
        )
        async def test_daily_extra_single_problem_uses_source_payload_and_visibility(
            monkeypatch,
            source,
            date,
            public,
        ):
            bot = _make_bot()
            cog = SlashCommandsCog(bot)
            interaction = _make_interaction()
            problem = _problem("100A")
            get_payload = AsyncMock(return_value=_payload(source, [problem]))
            create_embed = AsyncMock(return_value=sentinel.embed)
            create_view = AsyncMock(return_value=sentinel.view)
            monkeypatch.setattr(slash_commands_module, "get_daily_payload", get_payload)
            monkeypatch.setattr(slash_commands_module, "create_problem_embed", create_embed)
            monkeypatch.setattr(slash_commands_module, "create_problem_view", create_view)

            await cog.daily_extra_command.callback(
                cog,
                interaction,
                source=source,
                date=date,
                public=public,
            )

            interaction.response.defer.assert_awaited_once_with(ephemeral=not public)
            get_payload.assert_awaited_once_with(
                bot,
                date_str=date,
                source=source,
            )
            interaction.followup.send.assert_awaited_once_with(
                embed=sentinel.embed,
                view=sentinel.view,
                ephemeral=not public,
            )


        @pytest.mark.asyncio
        async def test_daily_extra_multiple_problems_uses_ordered_overview(monkeypatch):
            bot = _make_bot()
            cog = SlashCommandsCog(bot)
            interaction = _make_interaction()
            problems = [_problem("100A"), _problem("200B")]
            monkeypatch.setattr(
                slash_commands_module,
                "get_daily_payload",
                AsyncMock(return_value=_payload("sheep", problems)),
            )
            overview_embed = MagicMock(return_value=sentinel.embed)
            overview_view = MagicMock(return_value=sentinel.view)
            monkeypatch.setattr(
                slash_commands_module,
                "create_problems_overview_embed",
                overview_embed,
            )
            monkeypatch.setattr(
                slash_commands_module,
                "create_problems_overview_view",
                overview_view,
            )

            await cog.daily_extra_command.callback(
                cog,
                interaction,
                source="sheep",
                date="2026-06-02",
                public=True,
            )

            assert overview_embed.call_args.args[0] == problems
            assert overview_view.call_args.args[0] == problems
            interaction.followup.send.assert_awaited_once_with(
                embed=sentinel.embed,
                view=sentinel.view,
                ephemeral=False,
            )


        @pytest.mark.asyncio
        async def test_daily_extra_rejects_invalid_date_before_api(monkeypatch):
            bot = _make_bot()
            cog = SlashCommandsCog(bot)
            interaction = _make_interaction()
            get_payload = AsyncMock()
            monkeypatch.setattr(slash_commands_module, "get_daily_payload", get_payload)

            await cog.daily_extra_command.callback(
                cog,
                interaction,
                source="sheep",
                date="2026/06/02",
                public=False,
            )

            get_payload.assert_not_awaited()
            interaction.followup.send.assert_awaited_once_with(
                "errors.validation.date_format",
                ephemeral=True,
            )


        @pytest.mark.asyncio
        async def test_daily_extra_reports_not_found(monkeypatch):
            bot = _make_bot()
            cog = SlashCommandsCog(bot)
            interaction = _make_interaction()
            monkeypatch.setattr(
                slash_commands_module,
                "get_daily_payload",
                AsyncMock(return_value=None),
            )

            await cog.daily_extra_command.callback(
                cog,
                interaction,
                source="0x3f",
                date="2026-06-02",
                public=False,
            )

            bot.i18n.t.assert_any_call(
                "errors.validation.daily_extra_not_found",
                "zh-TW",
                source_label="0x3f",
                date="2026-06-02",
            )
            assert interaction.followup.send.await_args.kwargs["ephemeral"] is True


        @pytest.mark.asyncio
        async def test_daily_extra_rejects_unsafe_multi_problem_payload(monkeypatch):
            bot = _make_bot()
            cog = SlashCommandsCog(bot)
            interaction = _make_interaction()
            problems = [_problem("100A"), _problem("bad|id")]
            monkeypatch.setattr(
                slash_commands_module,
                "get_daily_payload",
                AsyncMock(return_value=_payload("sheep", problems)),
            )
            monkeypatch.setattr(
                slash_commands_module,
                "create_problems_overview_view",
                MagicMock(return_value=None),
            )

            await cog.daily_extra_command.callback(
                cog,
                interaction,
                source="sheep",
                date="2026-06-02",
                public=False,
            )

            interaction.followup.send.assert_awaited_once_with(
                "errors.validation.daily_extra_unsafe_payload",
                ephemeral=True,
            )


        @pytest.mark.asyncio
        @pytest.mark.parametrize(
            ("exception", "error_kind"),
            [
                (ApiProcessingError("processing"), "processing"),
                (ApiNetworkError("network"), "network"),
                (ApiRateLimitError(5), "rate_limit"),
                (ApiError(500, "failed"), "generic"),
            ],
        )
        async def test_daily_extra_maps_api_errors(monkeypatch, exception, error_kind):
            bot = _make_bot()
            cog = SlashCommandsCog(bot)
            interaction = _make_interaction()
            monkeypatch.setattr(
                slash_commands_module,
                "get_daily_payload",
                AsyncMock(side_effect=exception),
            )
            send_error = AsyncMock()
            monkeypatch.setattr(slash_commands_module, "send_api_error", send_error)

            await cog.daily_extra_command.callback(
                cog,
                interaction,
                source="sheep",
                date=None,
                public=False,
            )

            send_error.assert_awaited_once_with(
                interaction,
                error_kind,
                bot,
                ephemeral=True,
            )

- [ ] 3.2 Verify RED.

        .venv/bin/pytest -o addopts='' -o cache_dir=/tmp/leetcode-daily-discord-bot-pytest-cache -q tests/test_daily_extra_command.py

  Expected: command lookup and callback tests fail because /daily_extra is not registered; locale and label assertions fail because keys are absent.

- [ ] 3.3 Implement labels, locale keys, and the command.

  Add to SOURCE_LABELS in src/bot/utils/ui_constants.py:

        "sheep": "Sheep",
        "0x3f": "0x3f",

  Add these keys to all three locale files, translating values exactly:

  | Key | zh-TW | en-US | zh-CN |
  | --- | --- | --- | --- |
  | commands.daily_extra.description | 查詢 Sheep 或 0x3f 每日題目 | Query Sheep or 0x3f daily problems | 查询 Sheep 或 0x3f 每日题目 |
  | commands.daily_extra.source | 每日題目來源 | Daily problem source | 每日题目来源 |
  | commands.daily_extra.date | 指定日期（YYYY-MM-DD），不填則為今天 | Date (YYYY-MM-DD), defaults to today | 指定日期（YYYY-MM-DD），不填则为今天 |
  | commands.daily_extra.public | 是否公開顯示初始回覆（題目詳情仍為私密） | Show the initial response publicly (details remain private) | 是否公开显示初始回复（题目详情仍为私密） |
  | errors.validation.daily_extra_not_found | 找不到 {source_label} 在 {date} 的每日題目。 | No {source_label} daily problems were found for {date}. | 找不到 {source_label} 在 {date} 的每日题目。 |
  | errors.validation.daily_extra_unsafe_payload | 每日題目數量或題號無法安全顯示，請稍後再試。 | The daily problem set cannot be displayed safely. Please try again later. | 每日题目数量或题号无法安全显示，请稍后再试。 |
  | ui.embed.daily_extra_title | 📅 {source_label} Daily（{date}，共 {count} 題） | 📅 {source_label} Daily ({date}, {count} problems) | 📅 {source_label} Daily（{date}，共 {count} 题） |
  | ui.embed.daily_extra_footer | 📅 {source_label} Daily \u007c {date} | 📅 {source_label} Daily \u007c {date} | 📅 {source_label} Daily \u007c {date} |

  Add this command after daily_cn_command() in src/bot/cogs/slash_commands_cog.py:

        @app_commands.command(
            name="daily_extra",
            description=app_commands.locale_str("daily_extra.description"),
        )
        @app_commands.describe(
            source=app_commands.locale_str("daily_extra.source"),
            date=app_commands.locale_str("daily_extra.date"),
            public=app_commands.locale_str("daily_extra.public"),
        )
        @app_commands.choices(
            source=[
                app_commands.Choice(name="Sheep", value="sheep"),
                app_commands.Choice(name="0x3f", value="0x3f"),
            ]
        )
        async def daily_extra_command(
            self,
            interaction: discord.Interaction,
            source: str,
            date: str = None,
            public: bool = False,
        ):
            await interaction.response.defer(ephemeral=not public)
            locale = _get_locale(self.bot, interaction)
            i18n = self.bot.i18n

            if date and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
                await interaction.followup.send(
                    i18n.t("errors.validation.date_format", locale),
                    ephemeral=not public,
                )
                return

            try:
                payload = await get_daily_payload(
                    self.bot,
                    date_str=date,
                    source=source,
                )
                source_label = get_source_label(source)
                requested_date = date or (
                    payload.get("resolved_date")
                    if payload
                    else i18n.t("ui.embed.today", locale)
                )
                if not payload:
                    await interaction.followup.send(
                        i18n.t(
                            "errors.validation.daily_extra_not_found",
                            locale,
                            source_label=source_label,
                            date=requested_date,
                        ),
                        ephemeral=not public,
                    )
                    return

                problems = payload["problems"]
                resolved_date = payload["resolved_date"]
                footer_text = i18n.t(
                    "ui.embed.daily_extra_footer",
                    locale,
                    source_label=source_label,
                    date=resolved_date,
                )

                if len(problems) == 1:
                    problem = problems[0]
                    embed = await create_problem_embed(
                        problem_info=problem,
                        bot=self.bot,
                        domain="com",
                        is_daily=False,
                        date_str=resolved_date,
                        locale=locale,
                        footer_text=footer_text,
                    )
                    view = await create_problem_view(
                        problem_info=problem,
                        bot=self.bot,
                        domain="com",
                        locale=locale,
                    )
                else:
                    view = create_problems_overview_view(problems, "com")
                    if view is None:
                        await interaction.followup.send(
                            i18n.t(
                                "errors.validation.daily_extra_unsafe_payload",
                                locale,
                            ),
                            ephemeral=not public,
                        )
                        return
                    embed = create_problems_overview_embed(
                        problems,
                        "com",
                        title=i18n.t(
                            "ui.embed.daily_extra_title",
                            locale,
                            source_label=source_label,
                            date=resolved_date,
                            count=len(problems),
                        ),
                        source_label=source_label,
                        footer_icon_url=get_source_logo_url(source),
                        footer_text=footer_text,
                        bot=self.bot,
                        locale=locale,
                    )

                await interaction.followup.send(
                    embed=embed,
                    view=view,
                    ephemeral=not public,
                )
                self.logger.info(
                    "Sent %s daily challenge for %s with %d problems to user %s",
                    source,
                    resolved_date,
                    len(problems),
                    interaction.user.name,
                )
            except ApiProcessingError:
                await send_api_error(
                    interaction,
                    "processing",
                    self.bot,
                    ephemeral=not public,
                )
            except ApiNetworkError:
                await send_api_error(
                    interaction,
                    "network",
                    self.bot,
                    ephemeral=not public,
                )
            except ApiRateLimitError:
                await send_api_error(
                    interaction,
                    "rate_limit",
                    self.bot,
                    ephemeral=not public,
                )
            except ApiError as error:
                self.logger.error("API error in daily_extra command: %s", error)
                await send_api_error(
                    interaction,
                    "generic",
                    self.bot,
                    ephemeral=not public,
                )
            except Exception as error:
                self.logger.error(
                    "Unexpected error in daily_extra command: %s",
                    error,
                    exc_info=True,
                )
                await send_api_error(
                    interaction,
                    "generic",
                    self.bot,
                    ephemeral=not public,
                )

  Include this localized fallback key in the same locale edit:

  | Key | zh-TW | en-US | zh-CN |
  | --- | --- | --- | --- |
  | ui.embed.today | 今天 | today | 今天 |

- [ ] 3.4 Verify GREEN, locale parity, and existing commands.

  Add a locale parity test to tests/test_daily_extra_command.py:

        def test_daily_extra_locale_keys_have_parity():
            locale_dir = Path("src/bot/i18n/locales")
            documents = {
                path.stem: json.loads(path.read_text(encoding="utf-8"))
                for path in locale_dir.glob("*.json")
            }

            def flatten(value, prefix=""):
                keys = set()
                for key, child in value.items():
                    path = f"{prefix}.{key}" if prefix else key
                    keys.add(path)
                    if isinstance(child, dict):
                        keys.update(flatten(child, path))
                return keys

            expected = flatten(documents["zh-TW"])
            assert flatten(documents["en-US"]) == expected
            assert flatten(documents["zh-CN"]) == expected

  Run:

        .venv/bin/pytest -o addopts='' -o cache_dir=/tmp/leetcode-daily-discord-bot-pytest-cache -q \
          tests/test_daily_extra_command.py tests/test_slash_problem_command.py
        uv run --extra dev ruff check \
          src/bot/cogs/slash_commands_cog.py \
          src/bot/utils/ui_constants.py \
          tests/test_daily_extra_command.py

  Expected: command scenarios pass, locale key sets match, and existing /daily and /daily_cn tests remain green.

- [ ] 3.5 Commit the command and localization slice.

        git add \
          src/bot/cogs/slash_commands_cog.py \
          src/bot/utils/ui_constants.py \
          src/bot/i18n/locales/zh-TW.json \
          src/bot/i18n/locales/en-US.json \
          src/bot/i18n/locales/zh-CN.json \
          tests/test_daily_extra_command.py
        git commit -m "✨ feat(daily): add manual extra sources"

## Task 4: Lock privacy, document usage, and run completion verification

Files:

- Modify: tests/test_interaction_handler.py
- Modify: README.md
- Verify: all OpenSpec and source/test artifacts

Why:

The existing handler already sends view details ephemerally, but this is a user-critical concurrency guarantee and needs explicit preservation evidence. The public command also needs user-facing usage documentation.

Change Necessity:

No interaction source edit is required. A characterization assertion and README update are sufficient for this slice.

Impact / Compatibility:

No runtime behavior changes in InteractionHandlerCog. Documentation states that public controls the initial response only.

Verification:

Use the full commands in the plan Verification section.

- [ ] 4.1 Add the privacy characterization assertions.

  In TestInteractionHandler.test_problem_view_button_for_luogu_returns_full_problem_card(), retain all existing assertions and add:

        assert kwargs["ephemeral"] is True
        mock_interaction.edit_original_response.assert_not_awaited()

  This test should already pass before source changes; it is a compatibility lock, not a new failing behavior test.

  Also extend the unittest.mock import with sentinel and add this concurrent characterization test to TestInteractionHandler:

        @pytest.mark.asyncio
        async def test_problem_view_clicks_are_private_and_independent_per_user(
            self,
            cog,
            mock_bot,
            monkeypatch,
        ):
            def make_click(user_id: int, problem_id: str):
                interaction = AsyncMock(spec=discord.Interaction)
                interaction.type = discord.InteractionType.component
                interaction.data = {
                    "custom_id": f"problem|codeforces|{problem_id}|view"
                }
                interaction.user = MagicMock(id=user_id, name=f"user-{user_id}")
                interaction.response = AsyncMock()
                interaction.response.defer = AsyncMock()
                interaction.followup = AsyncMock()
                interaction.followup.send = AsyncMock()
                interaction.guild = MagicMock(id=987654321)
                interaction.guild_locale = None
                interaction.locale = discord.Locale.taiwan_chinese
                return interaction

            first = make_click(1, "100A")
            second = make_click(2, "200B")
            mock_bot.api.get_problem.side_effect = [
                {
                    "id": "100A",
                    "source": "codeforces",
                    "title": "First",
                    "link": "https://example.com/100A",
                },
                {
                    "id": "200B",
                    "source": "codeforces",
                    "title": "Second",
                    "link": "https://example.com/200B",
                },
            ]
            monkeypatch.setattr(
                interaction_handler_module,
                "create_problem_embed",
                AsyncMock(side_effect=[sentinel.first_embed, sentinel.second_embed]),
            )
            monkeypatch.setattr(
                interaction_handler_module,
                "create_problem_view",
                AsyncMock(side_effect=[sentinel.first_view, sentinel.second_view]),
            )

            await asyncio.gather(
                cog.on_interaction(first),
                cog.on_interaction(second),
            )

            first.response.defer.assert_awaited_once_with(ephemeral=True)
            second.response.defer.assert_awaited_once_with(ephemeral=True)
            assert first.followup.send.await_args.kwargs["ephemeral"] is True
            assert second.followup.send.await_args.kwargs["ephemeral"] is True
            first.edit_original_response.assert_not_awaited()
            second.edit_original_response.assert_not_awaited()

- [ ] 4.2 Run the privacy test against the current unchanged handler.

        .venv/bin/pytest -o addopts='' -o cache_dir=/tmp/leetcode-daily-discord-bot-pytest-cache -q \
          tests/test_interaction_handler.py::TestInteractionHandler::test_problem_view_button_for_luogu_returns_full_problem_card

  Expected: pass without modifying interaction_handler_cog.py.

- [ ] 4.3 Update README usage and examples.

  Add this row after /daily_cn:

        | /daily_extra <source> [date] [public] | Query Sheep or 0x3f daily problems<br>• source: sheep or 0x3f<br>• Optional: YYYY-MM-DD date<br>• Optional: public shows the initial response publicly<br>• Multi-problem results open as an overview; selected details are always private | None |

  Add these examples to the Daily Challenge Commands block:

        /daily_extra source:sheep
        /daily_extra source:0x3f date:2026-06-09
        /daily_extra source:sheep public:true

  Add one sentence below Multi-Problem Features:

        /daily_extra also uses overview mode when a daily source returns multiple problems. Clicking a problem ID opens a private full-problem card for the clicking user, even when the overview is public.

- [ ] 4.4 Run full verification and architecture review.

        .venv/bin/pytest -o addopts='' -o cache_dir=/tmp/leetcode-daily-discord-bot-pytest-cache -q \
          tests/test_daily_payload_reuse.py \
          tests/test_daily_extra_command.py \
          tests/test_slash_problem_command.py \
          tests/test_interaction_handler.py \
          tests/test_history_dates.py \
          tests/test_schedule_manager_cog.py
        uv run --extra dev ruff check .
        uv run --extra dev pytest -o cache_dir=/tmp/leetcode-daily-discord-bot-pytest-cache
        openspec validate add-daily-extra-command --strict --no-interactive
        python3 /home/usaya/.codex/aegis/scripts/aegis-workspace.py check --root .
        git diff --check

  Architecture review checklist:

  - No scheduler, DB, or config files changed.
  - No new custom-id prefix or interaction state exists.
  - get_daily() and v0.4 tests remain unchanged and green.
  - target cache keys are namespaced.
  - extra-source history calls are absent.
  - every accepted overview is complete and ordered.
  - selected detail responses remain ephemeral.
  - all locale keys have parity.

- [ ] 4.5 Commit documentation and compatibility evidence.

        git add README.md tests/test_interaction_handler.py
        git commit -m "📝 docs(daily): document extra source queries"

## Test Case Matrix

| Contract | Test evidence |
| --- | --- |
| Source-only API request | test_get_daily_by_source_sends_source_without_domain |
| Full ordered envelope | test_extra_daily_payload_preserves_order_and_skips_history |
| Cache target isolation | test_daily_payload_cache_isolated_by_target |
| In-flight reuse | test_extra_daily_payload_coalesces_identical_in_flight_requests |
| Exact source choices | test_daily_extra_source_choices_are_exact |
| Current and dated requests | test_daily_extra_single_problem_uses_source_payload_and_visibility |
| Default private / explicit public | same parameterized command test |
| Single full card | same command test with mocked card/view builders |
| Multi ordered overview | test_daily_extra_multiple_problems_uses_ordered_overview |
| Invalid date avoids API | test_daily_extra_rejects_invalid_date_before_api |
| 404 / empty payload | test_daily_extra_reports_not_found |
| 202/network/rate/API errors | test_daily_extra_maps_api_errors |
| Exact 25-button layout | test_daily_overview_view_preserves_exact_25_problem_order |
| More than 25 rejected | test_daily_overview_view_rejects_more_than_25_problems |
| Unsafe custom-id segment rejected | test_daily_overview_view_rejects_unsafe_routing_fields |
| Localized source/date footer | test_daily_overview_embed_accepts_daily_footer_override |
| Private selected detail | existing interaction view test plus ephemeral assertion |
| Concurrent click isolation | test_problem_view_clicks_are_private_and_independent_per_user |
| Locale parity | test_daily_extra_locale_keys_have_parity |
| Existing LeetCode and schedule regression | test_daily_payload_reuse.py, test_slash_problem_command.py, test_history_dates.py, test_schedule_manager_cog.py |

## Risks

- The planned localized "today" fallback must not remain an English literal in non-English locales.
- Changing create_problems_overview_view() to Optional requires checking every caller; current callers are /problem and the new /daily_extra.
- A partial or malformed upstream envelope must fail closed; do not filter invalid items and render a subset.
- Full tests instantiate file logging. Run inside the writable worktree and keep pytest cache in /tmp.
- If the full suite exposes unrelated baseline failures, compare against ba8cc10 before attributing them to this change; do not waive failures in touched paths.

## Retirement

- No production owner, legacy path, or compatibility normalization is retired.
- No fallback or adapter is added.
- The new API method and command should be removed together if oj-api-rs removes additional daily source support.
- The v0.4 LeetCode normalization remains only because existing configured backends may still use it; this change does not extend that compatibility path.

## Completion Evidence Required

- OpenSpec status shows 4/4 artifacts and strict validation succeeds.
- Focused and full pytest commands succeed.
- Ruff and git diff checks succeed.
- Locale key parity succeeds.
- Git diff confirms no scheduler, DB, config, or interaction-router source changes.
- Architecture review confirms one API owner, one cache owner, one UI safety owner, and one interaction protocol.
