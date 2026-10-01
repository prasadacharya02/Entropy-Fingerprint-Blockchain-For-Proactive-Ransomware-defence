"""Content of the ENTROPY project report.

The document is expressed as a flat list of blocks so that it can be
rendered to Word by ``report/build_report.py`` and measured before it is
written.  Block kinds:

    ("h1", text)          chapter heading (starts a new page)
    ("h2", text)          section heading
    ("h3", text)          sub-section heading
    ("p", text)           body paragraph
    ("bullets", [text])   bullet list
    ("numbers", [text])   numbered list
    ("refs", [text])      hanging-indent reference list
    ("table", dict)       {"caption", "header", "rows", "widths"}
    ("figure", dict)      {"path", "caption", "width_in"}
    ("code", text)        monospaced listing
    ("pagebreak", None)   explicit page break
"""

from __future__ import annotations

TITLE = ("Proactive Ransomware Defence using Entropy Fingerprints,\n"
         "Campaign Escalation and Blockchain Audit")
SHORT_TITLE = "ENTROPY — Ransomware Shield"

SUBTITLE = "ENTROPY — Ransomware Shield"
TAGLINE = ("A working purple-team laboratory for entropy-based ransomware detection,\n"
           "verified containment, hash-verified recovery and auditable response")


def blocks():
    b = []

    # ── 1. INTRODUCTION ───────────────────────────────────────
    b += [
        ("h1", "1. Introduction"),
        ("p",
         "Ransomware is the one class of malware whose whole purpose is to destroy the "
         "availability of data. The attacker does not need to steal a password or hide for "
         "months: it only has to overwrite files faster than the victim can react and then sell "
         "the decryption key back. Because the damage is done by ordinary file writes, the "
         "defence problem is fundamentally a race, and everything in this project follows from "
         "that observation."),
        ("p",
         "This report documents ENTROPY, a working purple-team laboratory that detects, "
         "contains, recovers from and audits ransomware attacks on a protected file estate. It "
         "runs as cooperating processes started by a single launcher: a monitor that watches "
         "the victim directory, an entropy analyser that scores every file event, a decision "
         "layer that fuses several independent signals, a response layer that terminates the "
         "attacker and quarantines evidence, a recovery layer that restores hash-verified clean "
         "copies, and an audit layer that writes a forensic report, anchors the incident in a "
         "ledger and shares the resulting threat fingerprint with other nodes."),
        ("h2", "1.1 Motivation"),
        ("p",
         "A conventional endpoint protection product is evaluated on how much malware it "
         "recognises, but against ransomware that question is incomplete. Encrypting a document "
         "is a legitimate operation performed through legitimate APIs, often by a process that "
         "is signed, unknown to reputation services, or simply the user's own productivity "
         "application. Signature matching and blocklists lose their footing against a "
         "polymorphic builder, while the behaviour that matters — reading a file and writing "
         "high-entropy content over it — is exactly what any archiver, database dump or media "
         "export does."),
        ("p",
         "What ransomware cannot hide is the statistical consequence of its own cryptography. Modern "
         "ciphers produce output indistinguishable from random data, and measured with Shannon entropy "
         "on a byte alphabet that output sits at the 8.0 bits-per-byte ceiling while ordinary documents, "
         "source code and databases sit far below it. Entropy is therefore an unavoidable fingerprint: "
         "imperfect, because photographs and archives are legitimately high-entropy, but present in "
         "every encryption-based attack and absent from most normal office work."),
        ("p",
         "The project treats entropy as an entry point rather than an answer. Absolute entropy matters "
         "only relative to the file's format and to its own history, and the strongest evidence is "
         "usually cross-file or cross-node — which the system expresses through a per-format envelope, "
         "an entropy-delta signal, a rolling event-rate window, an extension-change signal, a campaign "
         "tracker, hard confirmation signals such as ransom notes and backup-store tampering, and a "
         "federated exchange in which independent nodes confirm each other's detections."),
        ("h2", "1.2 Problem statement"),
        ("p",
         "The problem addressed here is the gap between detection and protection. Reporting an "
         "attack to a human operator is not enough, because by the time the alert is read the "
         "estate may already be encrypted; and a system that reacts aggressively without "
         "corroboration will eventually destroy a legitimate file, which is a failure of the "
         "same magnitude as missing an attack. The project therefore treats two quantities as "
         "equally important: detection latency, measured in file operations from the first "
         "malicious write to a containment decision, and the false quarantine rate, measured as "
         "legitimate files the defender itself destroyed."),
        ("h2", "1.3 Objectives"),
        ("p",
         "The objectives below are taken from the project requirement and are used as "
         "acceptance criteria in Section 6.3."),
        ("numbers", [
            "Provide a security-operations dashboard that continuously monitors changes in the "
            "victim file explorer and displays every event in real time.",
            "Keep the victim's own file explorer neutral: it shows file names, sizes and "
            "modification times, and never reveals attack intelligence such as encrypted-file "
            "counts, family attribution or quarantine contents.",
            "Respond automatically in the background — quarantine the suspicious file before "
            "the attack proceeds, terminate the responsible process, and move the file into the "
            "quarantine folder the operator creates at installation time.",
            "Recover the protected estate from hash-verified clean copies so that the victim "
            "ends the incident with the same bytes they started with.",
            "Produce auditable evidence for every incident: a forensic report, a dual-hash "
            "fingerprint and an entry in a tamper-evident ledger or a clearly labelled local "
            "ledger fallback.",
            "Publish honest, reproducible measurements, including the cases the system does not "
            "detect, rather than a demonstration that only ever shows success.",
        ]),
        ("h2", "1.4 Contributions"),
        ("p",
         "Five contributions are implemented and measured in the repository rather than "
         "described on a slide."),
        ("bullets", [
            "A format-aware entropy detector that scores every file event from absolute "
            "entropy, entropy delta against the file's own history, section-level entropy, "
            "event rate and extension change, and combines them into a 0–100 risk score.",
            "A campaign escalator that converts a sequence of individually sub-threshold events "
            "into a confirmed incident, so that slow attacks which never trip a speed threshold "
            "are still contained at the second file.",
            "A containment and recovery pipeline whose restore path refuses to restore "
            "encrypted-looking content, verified by a post-kill content scan that repairs files "
            "the attacker left half-written.",
            "An audit and sharing layer: a Solidity threat-logger contract with a clearly "
            "labelled local fallback, plus a federated fingerprint exchange with an "
            "independent-source confirmation rule that resists a poisoned node.",
            "A measurement harness — a deterministic benchmark battery, a byte-for-byte "
            "recovery drill and a multi-tenant exchange simulation — that regenerates every "
            "number quoted in this report.",
        ]),
        ("h2", "1.5 Scope and non-goals"),
        ("p",
         "The system is a controlled laboratory, not an endpoint product. It observes "
         "user-space directories, decides in user space and terminates processes with ordinary "
         "operating-system permissions: there is no kernel driver, no minifilter and no "
         "hypervisor introspection. The attacker is a purpose-built simulator confined to its "
         "own sandbox directory, so no real document is ever placed in the victim estate, and "
         "recovery means restoring a previously captured clean copy. The project makes no claim "
         "to decrypt ransomware output, which is impossible without the attacker's key. "
         "Chapter 8 lists these boundaries in full."),
    ]

    # ── 2. BACKGROUND ─────────────────────────────────────────
    b += [
        ("h1", "2. Background and Design Rationale"),
        ("p",
         "This chapter establishes the background the design relies on: how ransomware "
         "operates, why entropy is a usable fingerprint, what the alternatives are, and why the "
         "project combines them."),
        ("h2", "2.1 The attack and where it can be interrupted"),
        ("p",
         "A ransomware incident has a predictable shape: initial access, lateral movement and "
         "persistence measured in hours or days, backup destruction, data theft for double extortion, "
         "and finally the encryption stage — usually the shortest phase of the campaign. That stage is "
         "where the operation becomes visible on the filesystem, and each of its observable consequences "
         "maps to a defence opportunity: rewriting a file with random content raises its entropy, "
         "renaming many files changes their extensions, fast encryption produces a burst of events, "
         "dropping a note creates a recognisable filename, and deleting the backup store destroys the "
         "defender's own recovery capability."),
        ("h2", "2.2 Entropy as a fingerprint"),
        ("p",
         "Shannon entropy measures the average information content of a source. For a file "
         "treated as a sequence of bytes, the empirical entropy is H = − Σ p(b) · log₂ p(b), "
         "summed over the 256 possible byte values b, where p(b) is the relative frequency of "
         "byte value b in the sample. The result is bounded by 8.0 bits per byte, which is "
         "reached only when all byte values occur equally often. It is cheap to compute — a "
         "single pass over a 64 KiB sample — and stable between files of the same kind, which "
         "makes it suitable for a monitor that runs on every filesystem event."),
        ("figure", {
            "path": "figures/fig01_entropy_profile.png",
            "caption": "Figure 2.1 — Left: per-format entropy envelopes. Right: one document "
                       "observed before, during and after encryption, against the absolute "
                       "threshold (6.8) and the delta threshold (+2.0 bits from the file's own "
                       "history).",
            "width_in": 6.4,
        }),
        ("p",
         "The figure also shows why a single threshold is not enough. A photograph at 7.4 bits "
         "per byte is perfectly normal and must not alert; the same file rising from 4.6 to 7.9 "
         "in one second is an emergency. The detector therefore compares every reading against "
         "both the format envelope and the file's own previous readings, and counts an "
         "out-of-range value as evidence only when the margin is meaningful — the "
         "implementation requires the reading to exceed the format maximum by more than 0.5 "
         "bits before it scores."),
        ("h2", "2.3 Detection approaches considered"),
        ("p",
         "Five families of detection were considered. The choice matters because the "
         "false-quarantine budget of a real deployment is close to zero: a detector that "
         "quarantines a legitimate file has caused data loss."),
        ("table", {
            "caption": "Table 2.1 — Detection approaches considered and the reason for the "
                       "chosen combination.",
            "header": ["Approach", "Strength", "Weakness here", "Used"],
            "widths": [1.25, 1.5, 2.85, 0.75],
            "rows": [
                ["Signature / blocklist", "Cheap, exact, no false positives",
                 "Polymorphic builders are invisible; encryption is done by legitimate binaries",
                 "No"],
                ["Behavioural rules", "Explainable, deterministic, auditable",
                 "Needs calibrated thresholds; a single rule is easy to evade",
                 "Yes (default)"],
                ["Entropy statistics", "Family-agnostic; present in every encryption attack",
                 "Compressed formats are legitimately high-entropy; in-place encryption of "
                 "media is a blind spot", "Yes (primary)"],
                ["Supervised learning", "Combines many weak signals; closes some blind spots",
                 "Needs labelled data; a synthetic-trained model mislabels legitimate media "
                 "workloads", "Yes (opt-in)"],
                ["Deception / canaries", "High-confidence early warning",
                 "Covers only the planted files, not the rest of the estate", "No"],
            ],
        }),
        ("p",
         "No single row is sufficient, and the right response to the weaknesses is composition "
         "rather than escalation. The rule engine stays the default because it is the only "
         "configuration that never quarantined a legitimate file in the measured battery; the "
         "Random Forest is retained as an explicit alternative because it detects the media "
         "blind spot the rules miss, and its errors are measured rather than hidden."),
        ("h2", "2.4 Why corroboration beats a better threshold"),
        ("p",
         "The hardest cases for an entropy detector are genuinely ambiguous single events: a random "
         "payload in an unknown format is either an encrypted document or a legitimate binary blob, and "
         "no local threshold can separate them. Two design decisions resolve most of this without "
         "lowering thresholds. The first is temporal corroboration — the campaign tracker confirms an "
         "incident when two distinct files show encrypted-data signatures inside fifteen seconds, which "
         "is why the live demonstration kills the attack at the second file. The second is cross-node "
         "corroboration: a fingerprint confirmed by independent nodes is a fact about content, while a "
         "single node's sighting only raises the score and can never quarantine alone."),
        ("h1", "3. System Architecture"),
        ("p",
         "The system is organised as five cooperating surfaces: the victim estate that is "
         "protected, the monitoring and response pipeline that protects it, the SOC dashboard "
         "that reports on it, the victim console that the protected user sees, and the attacker "
         "console that provides the controlled adversary. All five run from a single launcher "
         "and communicate through the filesystem, a shared SQLite database, a socket channel "
         "and the blockchain connector."),
        ("h2", "3.1 Deployment and process model"),
        ("figure", {
            "path": "figures/fig02_topology.png",
            "caption": "Figure 3.1 — Deployment topology. The attacker console drives the "
                       "victim estate; the shield observes the estate, pushes events to the SOC "
                       "dashboard and restores clean copies; the victim console shows a neutral "
                       "file explorer with a PIN-protected evidence vault.",
            "width_in": 6.4,
        }),
        ("p",
         "The launcher is what makes the demonstration repeatable: it prepares the runtime directories "
         "including the install-time quarantine folder, generates the eighteen-file fixture estate "
         "clean, starts the pipeline with the victim directory in its watch list, and then starts the "
         "three web surfaces on fixed ports (SOC on 5000, victim on 5001, attacker on 8001). Each "
         "service runs in its own process, so a crash in one cannot disturb the pipeline."),
        ("h2", "3.2 Runtime pipeline"),
        ("figure", {
            "path": "figures/fig03_pipeline.png",
            "caption": "Figure 3.2 — Runtime pipeline. Every event passes through monitoring, "
                       "entropy analysis, corroboration, decision, response and finally "
                       "recovery and audit; the right-hand column lists the durable stores and "
                       "integrations each stage interacts with.",
            "width_in": 6.4,
        }),
        ("h2", "3.3 Module inventory"),
        ("table", {
            "caption": "Table 3.1 — Module inventory of the repository (about 17,300 lines of "
                       "Python).",
            "header": ["Package", "Responsibility"],
            "widths": [1.75, 4.65],
            "rows": [
                ["monitoring/", "Filesystem monitoring, event deduplication, bounded event "
                                "pipeline, threat-flag collection, decision engine and campaign "
                                "tracker, post-kill verification"],
                ["entropy/", "Shannon and section entropy, per-format envelope comparison, "
                             "threat scoring, per-file history"],
                ["response/", "Verified-PID termination, quarantine with SHA3-256 metadata, "
                              "versioned backup manager and restore, ransom-note detection, "
                              "forensic reports"],
                ["blockchain/", "ThreatLogger contract and ABI, Web3 connector with a durable "
                                "write worker, labelled local ledger fallback, fingerprint "
                                "exchange"],
                ["ai/", "Random Forest classifier with SHAP explanations, DQN agent with "
                        "checkpoint validation, training entry points"],
                ["dashboard/, victim_server/, attacker_server/",
                 "The three user-facing surfaces: SOC feed and charts, neutral explorer with "
                 "vault, and the controlled adversary with ten profiles"],
                ["benchmark/, tests/", "Deterministic scenario battery, recovery drill, "
                                       "exchange simulation, and 27 test modules"],
                ["storage/, config.py", "SQLite schema and migration, SHA-256 / SHA3-256 "
                                        "hashing, environment-driven configuration"],
            ],
        }),
        ("h2", "3.4 Data model"),
        ("p",
         "A single SQLite database is the operational record, written by the pipeline and read by the "
         "dashboard. It deliberately separates what the defender asked for from what actually happened — "
         "a distinction that matters in dry-run mode, where a response is planned and recorded but not "
         "executed. The schema is versioned and migrated additively."),
        ("table", {
            "caption": "Table 3.2 — Core columns of the events table (schema version 4).",
            "header": ["Column", "Meaning"],
            "widths": [1.85, 4.55],
            "rows": [
                ["timestamp, file_path, event_type",
                 "What was observed and when: create, modify, delete or rename"],
                ["entropy, entropy_delta",
                 "Absolute entropy of the sample and its change against the file's own history"],
                ["pid, process_name",
                 "Attributed process, when attribution was verified through the file's open "
                 "handles"],
                ["action, status",
                 "Decision taken (ignore, alert, terminate, terminate + quarantine) and its "
                 "display label"],
                ["requested_action, outcome, dry_run",
                 "What the response layer was asked to do, what it achieved, and whether the "
                 "operation was simulated"],
                ["restore_result",
                 "Result of the recovery attempt for the file, including the backup version "
                 "used"],
                ["engine, confidence, explanation, q_values",
                 "Which engine produced the verdict, how confident it was, the reasoning in "
                 "words and, for learned engines, the action values"],
            ],
        }),
    ]

    # ── 4. CORE TECHNIQUES ────────────────────────────────────
    b += [
        ("h1", "4. Core Techniques"),
        ("p",
         "This chapter describes the algorithms the pipeline is built from: how entropy is "
         "measured and scored, how a decision is reached and escalated, how containment is "
         "performed safely, how clean history is maintained so that recovery is possible, and "
         "how incidents are anchored and shared."),
        ("h2", "4.1 Entropy measurement and scoring"),
        ("p",
         "Entropy is computed with a single pass over a bounded sample of up to 65,536 bytes, which "
         "keeps the cost of analysis independent of file size; the full-file SHA-256 hash is computed "
         "separately so content identity is never estimated from a sample. Each reading is decomposed "
         "into the first, middle and last third of the sample so that a partly overwritten file produces "
         "a high end-section entropy while the start still looks like the original document, and the "
         "per-path history is transferred across a rename so an attacker cannot reset a file's baseline "
         "by changing its name."),
        ("code",
         "Algorithm 4.1 — entropy scoring (entropy/entropy_calculator.py)\n"
         "-------------------------------------------------------------------------\n"
         "input : file path, sample s (<= 65536 bytes), history H of previous readings\n"
         "output: entropy value, threat score in [0,100], human-readable indicators\n"
         "\n"
         " 1  H_now   <- -sum_b p(b) * log2 p(b)   over the 256 byte values of s\n"
         " 2  H_start, H_mid, H_end <- entropy of the three sections of s\n"
         " 3  delta   <- H_now - last(H)                 # own history, not a global value\n"
         " 4  normal  <- NORMAL_ENTROPY_RANGES[extension]  or  (3.0, 7.5) if unknown\n"
         " 5  score   <- 0 ;  indicators <- []\n"
         " 6  if H_now >= 6.8 and extension is unknown:\n"
         " 7      score <- score + 40        # high-entropy content, unrecognised format\n"
         " 8  if H_now > normal.max + 0.5 and extension is known:\n"
         " 9      score <- score + 40        # meaningfully above the format envelope\n"
         "10  if |delta| >= 2.0:\n"
         "11      score <- score + 30        # the file changed character since last seen\n"
         "12  if (H_end - H_start) > 2.0:\n"
         "13      score <- score + 15        # partial encryption in progress\n"
         "14  return min(score, 100), indicators"),
        ("table", {
            "caption": "Table 4.1 — Per-format entropy envelopes used by the detector "
                       "(bits per byte).",
            "header": ["Format", "Range", "Format", "Range", "Format", "Range"],
            "widths": [0.95, 1.1, 0.95, 1.1, 0.95, 1.35],
            "rows": [
                [".txt", "3.0 – 5.5", ".docx", "6.0 – 7.5", ".png", "6.5 – 7.5"],
                [".py", "4.0 – 6.0", ".xlsx", "6.0 – 7.5", ".jpg / .jpeg", "7.0 – 7.8"],
                [".csv", "4.0 – 6.0", ".doc", "6.0 – 7.5", ".mp4", "7.0 – 7.9"],
                [".dat", "4.0 – 6.5", ".pdf", "6.5 – 7.8", ".zip", "7.5 – 8.0"],
                [".exe", "5.0 – 7.2", "unknown", "3.0 – 7.5", "ciphertext", "≈ 7.8 – 8.0"],
            ],
        }),
        ("h2", "4.2 From score to decision"),
        ("p",
         "The decision layer converts a scored event into one of four actions. Before any "
         "engine is consulted, three hard-confirmation signals are evaluated, because each "
         "establishes a fact that no statistical model should be allowed to argue with:"),
        ("bullets", [
            "a ransom note has appeared — detected by filename pattern and by a phrase list in "
            "the file's head, which catches notes that arrive under unexpected names;",
            "the defender's own stores have been tampered with — a deletion inside the backup "
            "or quarantine directory, or a running command line that targets them;",
            "the content fingerprint has already been confirmed by two or more independent "
            "nodes through the federated exchange.",
        ]),
        ("p",
         "Any of those signals short-circuits the decision to terminate and quarantine with confidence "
         "1.0, regardless of which engine is active. Otherwise the configured engine scores the event — "
         "rules by default, Random Forest or DQN when explicitly selected — and the campaign tracker "
         "then has the opportunity to escalate (Figure 4.1)."),
        ("figure", {
            "path": "figures/fig04_decision_flow.png",
            "caption": "Figure 4.1 — Decision flow. Hard-confirmation signals bypass all "
                       "scoring; otherwise scoring and campaign escalation decide the action, "
                       "and only a terminate-level decision reaches the response layer.",
            "width_in": 6.4,
        }),
        ("table", {
            "caption": "Table 4.2 — Action levels and the behaviour of the response layer.",
            "header": ["Level", "Trigger", "Behaviour"],
            "widths": [1.25, 2.2, 2.95],
            "rows": [
                ["0 — IGNORE", "Score below 40 with no hard or campaign signal",
                 "Event is stored and shown in the live feed"],
                ["1 — ALERT", "40 ≤ score < 70, or corroboration from a single external node",
                 "Event is stored with its explanation and raised on the alerts panel; no "
                 "filesystem action"],
                ["2 — TERMINATE", "Confirmed incident where the process is verified but "
                                  "quarantine is deferred",
                 "The attributed process is terminated; the file is left in place"],
                ["3 — TERMINATE + QUARANTINE",
                 "Score ≥ 70 with corroboration, a hard-confirmation signal, or a confirmed "
                 "campaign",
                 "Process terminated, file moved to quarantine with dual-hash metadata, clean "
                 "version restored, incident reported and anchored"],
            ],
        }),
        ("h2", "4.3 Campaign escalation"),
        ("p",
         "The campaign tracker exists because the most realistic attacks are not the fastest "
         "ones. An operator encrypting two files per second never trips a threshold expressed "
         "in events per second, and each individual file may score below the quarantine bar. "
         "What such an attack cannot avoid is a pattern: several distinct files that have "
         "become high-entropy and have either changed extension or jumped by two bits from "
         "their own history, inside a short window."),
        ("code",
         "Algorithm 4.2 — campaign escalation (monitoring/pipeline_runner.py)\n"
         "-------------------------------------------------------------------------\n"
         "state : recent -> list of (path, action, verified_pid, timestamp)\n"
         "config: CAMPAIGN_MIN_FILES = 2, CAMPAIGN_WINDOW_SECONDS = 15\n"
         "\n"
         " 1  qualifies(e):\n"
         " 2      return e.entropy >= 6.8\n"
         " 3         and (abs(e.delta) >= 2.0 or e.extension_changed)\n"
         "\n"
         " 4  on_event(e):\n"
         " 5      drop entries of recent older than CAMPAIGN_WINDOW_SECONDS\n"
         " 6      if decision(e) >= ALERT and qualifies(e):\n"
         " 7          record (e.path, decision(e), verified_pid(e)) in recent\n"
         " 8      others <- distinct paths in recent, other than e.path, with action >= ALERT\n"
         " 9      if decision(e) >= ALERT and |others| >= CAMPAIGN_MIN_FILES - 1:\n"
         "10          escalate decision(e) to TERMINATE + QUARANTINE\n"
         "11          sweep <- others                    # quarantine and restore them too\n"
         "12          kill_target <- verified pid of the most recent recorded event\n"
         "13      return decision(e), sweep, kill_target"),
        ("p",
         "In the live demonstration this rule is what limits the damage to two files out of "
         "eighteen. The first file raises an alert with a score of 60; the second file is "
         "renamed to the ransomware extension, and moments later the campaign is confirmed. The "
         "response terminates the attacker process in the middle of its third file, sweeps the "
         "two files already processed, and hands the estate to the post-kill verification pass. "
         "Figure 4.2 shows the trace with the attacker's own clock and the state of the estate "
         "at the moment of the kill."),
        ("figure", {
            "path": "figures/fig05_campaign_timeline.png",
            "caption": "Figure 4.2 — Left: containment trace of the live WannaCry "
                       "demonstration, from the first attacker file operation to the post-kill "
                       "repair. Right: entropy of the affected files at kill time; files 4–18 "
                       "were never reached.",
            "width_in": 6.4,
        }),
        ("h2", "4.4 Containment"),
        ("p",
         "Containment has two destructive components — killing a process and moving a file — "
         "and both are written conservatively. Termination requires a verified process "
         "identifier: only the process currently holding the file open is eligible, and "
         "candidates inferred from recency are recorded for the report but never killed. The "
         "terminator is zombie-aware, treating an already-reaped child as success rather than "
         "falling into a force-kill path, and a whitelist of defender tooling markers prevents "
         "the shield from killing itself or its own services."),
        ("p",
         "Quarantine moves the file into the directory the operator created at installation time, with a "
         "JSON sidecar recording the original path, the triggering entropy reading, the timestamp, the "
         "attributed process and the content's dual fingerprint (SHA3-256 primary, SHA-256 for "
         "interoperability). Quarantined content is evidence, not a backup: the simulator overwrites "
         "files with random bytes and keeps no key, exactly as real ransomware does, so recovery always "
         "comes from the backup store and the vault is a forensic viewer, never a decryption tool."),
        ("h2", "4.5 Clean history and restoration"),
        ("p",
         "Recovery is only as good as the backups it restores from, and the subtle failure mode is a "
         "backup that captures encrypted content as if it were clean. An earlier iteration did exactly "
         "that: a spreadsheet encrypted to 7.88 bits per byte fell inside a lenient per-format range, "
         "was labelled clean, and was later written back over the victim's file. The strict clean rule "
         "eliminates the failure — a captured version is clean only if its entropy lies inside the "
         "format's envelope with no margin and differs from the previous clean version by less than two "
         "bits, the same delta the detector treats as a change of character."),
        ("code",
         "Algorithm 4.3 — strict clean labelling and restore (response/backup_manager.py)\n"
         "-------------------------------------------------------------------------\n"
         " 1  capture(path, event_time):\n"
         " 2      H <- entropy(sample of path)\n"
         " 3      normal <- NORMAL_ENTROPY_RANGES[extension]   # None if the format is unknown\n"
         " 4      last  <- entropy of the last version labelled clean\n"
         " 5      clean <- (normal is not None)\n"
         " 6               and (normal.min <= H <= normal.max)\n"
         " 7               and (last is None or |H - last| < 2.0)\n"
         " 8      store blob sha256(content); append version to manifest with clean flag\n"
         "\n"
         " 9  restore(path):\n"
         "10      candidate <- newest version of path with clean = true\n"
         "11      if candidate is None: return CONTAINED, NOT RESTORED\n"
         "12      if sha256(blob) != candidate.sha256: return REFUSED, integrity failure\n"
         "13      write blob over path  (or simulate, when dry-run is enabled)\n"
         "14      if original name is free: rename path back to its pre-attack name\n"
         "15      return RESTORED"),
        ("h2", "4.6 Post-kill verification"),
        ("p",
         "A process killed mid-write leaves a file the pipeline may never have scored above the alert "
         "bar. After a confirmed campaign the pipeline therefore walks the protected estate once and "
         "compares each file's current SHA-256 against the hash of its newest clean backup version; "
         "files that differ are quarantined and restored, and their entropy history is re-primed. The "
         "repair signal is content, not entropy level, and that distinction was learned the hard way: an "
         "entropy-based rule false-quarantined eleven clean photographs in an intermediate version, "
         "because 7.4 bits per byte is a normal reading for a JPEG."),
        ("h2", "4.7 Learned engines"),
        ("p",
         "Two optional learned engines ship with the system, both disabled by default. The Random Forest "
         "is trained on a seeded, versioned synthetic dataset; its feature schema extends the DQN state "
         "vector with in_normal_range, which encodes whether a reading is inside the format envelope — "
         "precisely the signal the rule engine uses to keep legitimate media quiet, and its influence is "
         "visible in the SHAP explanations attached to each incident. Both learned engines are wrapped "
         "so that any inference error falls back to the rule engine."),
        ("h2", "4.8 Audit and federated sharing"),
        ("p",
         "Every confirmed incident produces three artefacts: a forensic report, a ledger entry and, when "
         "the quarantined content's real hash is known, a published fingerprint. The ledger has two "
         "implementations behind one interface — a Solidity ThreatLogger contract on a local Ganache "
         "chain whose logThreat function is restricted to the contract owner, and a local SQLite "
         "fallback. The two are never conflated: the connector reports a mode of ganache, fallback or "
         "none, and the dashboard displays that mode beside the transaction count."),
        ("figure", {
            "path": "figures/fig07_audit_flow.png",
            "caption": "Figure 4.3 — Audit and sharing. A confirmed incident becomes a forensic "
                       "report, a ledger entry and a published fingerprint; the exchange "
                       "confirmation rule requires two independent sources before a "
                       "fingerprint may quarantine on its own.",
            "width_in": 6.4,
        }),
        ("p",
         "Sharing is deliberately asymmetric. A node publishes a fingerprint only for content it "
         "actually quarantined and only when it holds that content's real hash; a suspicion, an alert, a "
         "path hash or an already-deleted file is never published. On the read side, one sighting from a "
         "single node is corroboration worth twenty-five points and can lift an ignored event to an "
         "alert, while two or more independent sources are a hard confirmation that quarantines "
         "outright."),
        ("h1", "5. Implementation and Operation"),
        ("p",
         "This chapter describes how the design is realised in the repository and how the "
         "system is operated: the procedure for running the laboratory, the three user-facing "
         "surfaces and the engineering practices that keep the project reproducible."),
        ("h2", "5.1 Operating procedure"),
        ("code",
         "# One-command operation (examiner path)\n"
         "python install.py                      # creates the quarantine folder at install time\n"
         "python -m venv .venv && source .venv/bin/activate\n"
         "pip install -r requirements.txt\n"
         "python lab.py                          # monitor + SOC + victim + attacker\n"
         "\n"
         "# Surfaces\n"
         "http://127.0.0.1:5000    SOC dashboard   - live feed, entropy graph, alerts, ledger\n"
         "http://127.0.0.1:5001    victim console  - neutral file explorer + evidence vault\n"
         "http://127.0.0.1:8001    attacker console- launch a controlled attack\n"
         "\n"
         "# Measurement (regenerates every number in Chapter 7)\n"
         "python -m benchmark                     # detection battery: attacks + workloads\n"
         "python -m benchmark.recovery_drill      # byte-for-byte recovery and RTO\n"
         "python -m benchmark.exchange_simulation # multi-tenant federated sharing\n"
         "python -m unittest discover -s tests    # automated suite"),
        ("h2", "5.2 The three surfaces"),
        ("p",
         "The SOC dashboard is the operator's view: a live event feed driven by socket push rather than "
         "polling, with new rows emitted about every 0.4 seconds, alongside the entropy chart, the "
         "alerts panel with each decision's explanation, the quarantine browser, the ledger status with "
         "its explicit mode label and the forensic reports. A status banner makes the pipeline's own "
         "health visible — whether the monitor is running, whether it is watching the intended folder, "
         "and whether destructive responses are enabled or the system is in dry-run."),
        ("p",
         "The victim console is deliberately dull, because a real user's file explorer does not know "
         "that an attack is happening: it returns only names, sizes, modification times and icons, with "
         "no encrypted-file counts or family attribution. Quarantine contents sit behind a vault login "
         "using a constant-time comparison and an eight-hour session; the vault can list and describe "
         "evidence, and cannot decrypt anything, which the interface states plainly."),
        ("p",
         "The attacker console exists so that the demonstration is honest about what is tested. It "
         "offers ten ransomware profiles — historical names label speed and naming behaviour, not real "
         "malware — with controls for speed, seed and target count. Each run is launched as a separate "
         "process whose child is reaped deterministically, which is what lets the defender's termination "
         "be reported as an immediate success rather than a force-kill, and every engine is confined to "
         "the victim estate by an explicit path check."),
        ("h2", "5.3 Engineering practices"),
        ("p",
         "Four practices explain the reliability of the demonstration. Destructive actions default to "
         "safe, with requested_action, outcome and dry_run recorded separately so a planned response is "
         "never reported as a success. Every decision is explainable at the point of record, with the "
         "engine, its confidence and a human-readable explanation persisted alongside the event. The "
         "measurement harness is part of the product, so a number in this report cannot drift away from "
         "the system's behaviour. And the repository is kept reproducible: deterministic fixtures, "
         "seeded benchmarks and a pinned dependency set."),
        ("h1", "6. Testing and Verification"),
        ("p",
         "Verification happened at three levels: an automated unit and integration suite that "
         "runs on every change, an end-to-end live demonstration that exercises the whole "
         "pipeline against a real attacker process, and a set of acceptance checks derived from "
         "the project requirements."),
        ("h2", "6.1 Automated test suite"),
        ("p",
         "The suite is organised into twenty-seven modules that mirror the architecture. The tests that "
         "matter most for safety assert the absence of action: that a legitimate high-entropy file is "
         "not quarantined, that a terminate decision without a verified process identifier does not kill "
         "an unrelated process, that the defender never terminates its own tooling, and that a restore "
         "refuses a blob whose hash does not match its manifest entry."),
        ("table", {
            "caption": "Table 6.1 — Areas covered by the automated suite (27 modules, 145 test "
                       "functions; 126 execute and pass in the default environment, the "
                       "remainder skipped when optional dependencies such as torch or web3 are "
                       "absent).",
            "header": ["Area", "Representative assertions"],
            "widths": [1.85, 4.55],
            "rows": [
                ["Entropy and scoring",
                 "Known-content entropy; per-format envelopes; delta and section signals; "
                 "behaviour on unknown extensions"],
                ["Decision and campaign",
                 "Action thresholds; hard-confirmation short-circuit; escalation at the second "
                 "qualifying file; no escalation on unrelated edits"],
                ["Response safety",
                 "Verified-PID requirement; self-kill protection; dry-run leaves the file in "
                 "place; requested action recorded separately from outcome"],
                ["Backup and restore",
                 "Strict clean rule rejects ciphertext captures; hash verification before "
                 "restore; rename-back only when the original name is free"],
                ["Recovery and exchange",
                 "Byte-for-byte equality of the restored estate; single sighting cannot "
                 "quarantine; two independent sources confirm; workloads publish nothing"],
                ["Configuration and dashboards",
                 "Invalid environment values rejected; vault session expiry; control endpoints "
                 "require a token; neutral victim payload; simulator confined to the estate"],
            ],
        }),
        ("h2", "6.2 End-to-end verification"),
        ("p",
         "The end-to-end test is the demonstration itself, executed against a live attacker "
         "process and verified afterwards by content rather than by assertion: the estate is "
         "snapshotted before the attack, the attack is launched from the attacker console, the "
         "pipeline detects, escalates, terminates and restores, and the estate is then compared "
         "against the snapshot — a ZIP content hash for the archive-visible state and a byte "
         "comparison for the documents."),
        ("table", {
            "caption": "Table 6.2 — Verified end-to-end trace of the live WannaCry "
                       "demonstration.",
            "header": ["Observation", "Result"],
            "widths": [2.85, 3.55],
            "rows": [
                ["Files reached by the attacker", "2 of 18, killed during the third"],
                ["Time from first attack operation to termination", "2.7 seconds"],
                ["Termination result", "Verified PID, immediate exit, exit code 42"],
                ["Ransomware-suffixed files left on disk", "0"],
                ["Files restored to pre-attack content", "18 of 18, byte-for-byte"],
                ["Quarantined evidence items", "3, held with dual-hash metadata and forensic "
                                               "reports"],
                ["Post-kill repair", "One mid-write file detected by content hash, quarantined "
                                     "and restored"],
                ["Dashboard and ledger state after the incident",
                 "quarantined = 3, recovered = 3, threats = 4, events = 13; ledger mode "
                 "reported as the labelled local fallback"],
            ],
        }),
        ("h2", "6.3 Acceptance against the stated objectives"),
        ("table", {
            "caption": "Table 6.3 — Acceptance checks against the objectives of Section 1.3.",
            "header": ["Objective", "Evidence", "Status"],
            "widths": [2.15, 3.35, 0.9],
            "rows": [
                ["Real-time SOC feed of victim file changes",
                 "Socket push of new events about every 0.4 s, verified with a frame-level "
                 "check as well as visually", "Met"],
                ["Victim explorer shows no attack details",
                 "The victim API returns only name, size, modified time and icon; quarantine "
                 "content sits behind the vault", "Met"],
                ["Automatic response before the attack proceeds",
                 "Campaign escalation, verified-PID termination and quarantine at the second "
                 "file of eighteen", "Met"],
                ["Quarantine folder created by the operator at install time",
                 "install.py and the launcher both create and log the quarantine directory; "
                 "the path is configurable", "Met"],
                ["Recovery of the protected estate",
                 "18/18 files restored byte-for-byte in the live demonstration; the general "
                 "case is measured in Chapter 7", "Met"],
                ["Auditable evidence per incident",
                 "Forensic report, dual-hash fingerprint and a ledger entry with an explicit "
                 "mode label", "Met"],
                ["Honest reporting of failures",
                 "The image blind spot, the model false quarantines and the no-baseline "
                 "recovery losses are measured and published", "Met"],
            ],
        }),
        ("h2", "6.4 Reproducibility"),
        ("p",
         "Every measurement in this report is regenerated by a single command. The benchmark "
         "uses seeded content and timing and builds a fresh decision engine per scenario so "
         "that scenarios cannot contaminate each other's history; the recovery drill performs a "
         "real capture, attack replay, containment and restore on a throwaway estate and "
         "verifies the result byte-for-byte; and the report's figures are generated by script "
         "rather than drawn by hand, so the document and the measurements cannot diverge."),
    ]

    # ── 7. RESULTS ────────────────────────────────────────────
    b += [
        ("h1", "7. Results and Evaluation"),
        ("p",
         "This chapter reports what the system actually does. All numbers come from the "
         "deterministic harness described in Chapter 6 and can be regenerated; nothing is "
         "projected, and failures are reported alongside successes."),
        ("h2", "7.1 Methodology"),
        ("p",
         "The detection battery consists of eight attack scenarios and seven legitimate workloads "
         "(document editing, archive creation, photo import, video write, a git checkout burst, CSV "
         "export and a database dump), each run with three seeds and in two baseline modes — with and "
         "without the production startup snapshot — giving 48 attacked runs and 21 legitimate runs. "
         "Scenarios are deterministic: contents, sizes, order and timing derive from the seed and the "
         "monitor's event-rate window is simulated with the scenario's own clock. Detection is measured "
         "at file-event level, and a quarantine against a legitimate workload is counted separately as a "
         "false quarantine, because that is data loss, while an alert on a busy but harmless workload is "
         "a false positive but not data loss."),
        ("h2", "7.2 Detection performance"),
        ("p",
         "The default rule engine detects 42 of 48 attacked runs (87.5 per cent) at a median of "
         "one to two file operations, with zero false quarantines across all 21 legitimate "
         "runs. Seven of the eight attack scenarios are detected in every run; the exception is "
         "the image blind spot, which the rules do not detect at all. The Random Forest, "
         "evaluated on the same event streams, detects 48 of 48 runs and closes the blind spot, "
         "but false-quarantines six legitimate runs from the photo and video workloads."),
        ("figure", {
            "path": "figures/fig08_detection_results.png",
            "caption": "Figure 7.1 — Detection results. Left: per-scenario detection for both "
                       "engines, six seeded runs each. Right: the headline trade-off — the "
                       "learned engine trades a zero-false-quarantine guarantee for complete "
                       "detection of the tested scenarios.",
            "width_in": 6.4,
        }),
        ("p",
         "The rule engine's false positives come from the git-burst workload — forty small text files "
         "created in a fraction of a second — which trips the event-rate signal three times out of "
         "three. Those runs alert and are recorded, and the files are left alone: a burst of file "
         "creation is what a checkout looks like and also what a fast encryptor looks like. Separating "
         "the two metrics shows that this case costs attention rather than data."),
        ("h2", "7.3 Recovery performance"),
        ("p",
         "Detection alone does not protect anything, so the recovery drill measures the full "
         "loop: capture a real baseline, replay a real attack, run the real detection and "
         "response chain, restore from the real backup store, and verify the estate "
         "byte-for-byte. Across all scenarios and both baseline modes, 111 of 246 attacked "
         "files were recovered (45.1 per cent), 12 were contained but not restored, and 123 "
         "were lost; the median recovery time was eight file operations and the response work "
         "itself took nine to twenty-seven milliseconds per scenario."),
        ("figure", {
            "path": "figures/fig10_recovery.png",
            "caption": "Figure 7.2 — Recovery drill outcomes per scenario. With a startup "
                       "baseline the rename-based attacks recover completely; without one, "
                       "nothing captured before monitoring started can be restored, which is "
                       "the honest worst case.",
            "width_in": 6.4,
        }),
        ("p",
         "The distribution of outcomes is more informative than the headline. With the production "
         "baseline the four rename-based scenarios recover every affected file byte-for-byte, and the "
         "pre-existing-estate scenario recovers four of four because a legitimate edit had produced a "
         "clean capture. The image blind spot accounts for most of the losses, and the twelve contained- "
         "but-not-restored files are the honest middle case: the content was preserved for manual "
         "recovery, but the pipeline refused to restore it because it looked encrypted and no clean "
         "version existed."),
        ("h2", "7.4 Latency"),
        ("p",
         "Detection latency decides whether containment happens before or after the estate is encrypted. "
         "In the benchmark, 42 of 48 attacked runs were detected on the first file operation and the "
         "remaining six on the second; in the live demonstration containment completed 2.7 seconds after "
         "the attacker's first write. The monitor polls at 0.2 seconds and the dashboard pushes at 0.4 "
         "seconds, so an event is visible to the operator within roughly half a second of the operation "
         "that caused it."),
        ("h2", "7.5 Federated exchange"),
        ("p",
         "The exchange simulation runs four tenants against one shared registry, each with its "
         "own history and estate, driving the real decision and response chain. The test "
         "payload is a ransom note plus in-place encryption of a deterministic block; the "
         "ambiguous case is that block alone, written to an unknown extension with no note, no "
         "baseline and no history, which scores 40 and would only ever be an alert on its own "
         "evidence."),
        ("table", {
            "caption": "Table 7.1 — Federated exchange simulation, phase by phase.",
            "header": ["Phase", "Tenant", "Exchange state", "Local score", "Decision"],
            "widths": [1.35, 1.15, 1.5, 0.95, 1.45],
            "rows": [
                ["Cold start", "charlie", "empty", "40", "ALERT"],
                ["Seeding", "alpha", "—", "note + 70", "QUARANTINE ×2"],
                ["Single sighting", "delta", "1 source", "40 (+25)", "ALERT (corroborated)"],
                ["Seeding", "bravo", "1 → 2 sources", "note + 70", "QUARANTINE ×2"],
                ["Warm start", "charlie (fresh)", "2 sources", "40", "QUARANTINE (confirmed)"],
                ["Workload", "charlie", "threat-only", "0", "IGNORE ×4, nothing published"],
            ],
        }),
        ("p",
         "The result is the effect the design was aiming for: a node with no local history quarantines a "
         "file that is locally ambiguous, purely because two independent nodes have already contained "
         "that exact content, while the single-sighting case restrains itself to an alert and the "
         "workload phase shows the exchange does not become a false-positive amplifier. On the ledger "
         "side the evaluation environment has no chain node running, so the connector reports the "
         "labelled local fallback with four transactions, and the dashboard shows both the mode and the "
         "count — an ordered local record, not an immutable chain."),
        ("h2", "7.6 Discussion"),
        ("p",
         "Three conclusions follow from the measurements. First, the strongest improvement to detection "
         "came not from a better threshold but from combining weak signals across events and nodes: "
         "campaign escalation turns a sub-threshold second file into a contained incident, and exchange "
         "confirmation turns a locally ambiguous payload into a decision. Second, safety and detection "
         "rate trade against each other and the trade must be explicit. Third, recovery quality is "
         "dominated by data availability rather than response speed: the scenarios that lose files are "
         "those where nothing clean was ever captured."),
        ("h1", "8. Limitations and Future Work"),
        ("p",
         "The value of a security evaluation depends on how honestly it states what the system "
         "cannot do. This chapter lists the known limitations, including the ones the "
         "measurements above expose, and the work that follows from them."),
        ("h2", "8.1 Known limitations"),
        ("table", {
            "caption": "Table 8.1 — Limitations of the current implementation.",
            "header": ["Limitation", "Consequence", "Mitigation today"],
            "widths": [1.75, 2.35, 2.3],
            "rows": [
                ["Image blind spot: in-place encryption of already-compressed media without a "
                 "rename",
                 "Entropy stays inside the format envelope, so the rule engine detects 0 of 6 "
                 "runs of this scenario",
                 "Published openly; the Random Forest closes it but is not the default because "
                 "of its false quarantines"],
                ["Process attribution is best-effort",
                 "A process that does not hold the file open at decision time cannot be "
                 "identified",
                 "Only verified PIDs are killed; unverified candidates are recorded for manual "
                 "follow-up"],
                ["Ransom-note detection is signature-based",
                 "A note with unknown wording and an unexpected filename relies on the entropy "
                 "and campaign signals alone",
                 "Filename patterns plus a phrase list, treated as a hard confirmation when "
                 "matched"],
                ["No kernel-level enforcement",
                 "The system runs in user space and can be evaded by a sufficiently privileged "
                 "adversary",
                 "Explicitly a laboratory; the minifilter or eBPF path is documented as future "
                 "work"],
                ["Quarantined content cannot be decrypted",
                 "Evidence is preserved but not recoverable as data",
                 "Stated in the interface; the simulator keeps no key, as real ransomware does "
                 "not"],
                ["Files with no clean version are not restorable",
                 "Content that existed only in encrypted form, or was deleted outside a "
                 "protected store, is lost",
                 "Counted explicitly in the recovery drill rather than hidden"],
                ["Learned engines train on synthetic data",
                 "Model accuracy on synthetic data does not predict real-world prevalence",
                 "The rule engine stays the default; model metrics are reported on the seeded "
                 "split and the benchmark"],
                ["The exchange is a simulated network",
                 "Several tenants share one local store rather than communicating over a "
                 "network",
                 "The registry API allows the store to be replaced by a network backend "
                 "without changing decision logic"],
            ],
        }),
        ("h2", "8.2 Threats to validity"),
        ("p",
         "The benchmark results are internally valid — the scenarios are deterministic and the decision "
         "path is the production one — but their external validity is limited. The attacker is a "
         "simulator that does not attempt evasion and does not interleave decoy activity; the estate is "
         "eighteen small documents rather than a mixed file server; and the recovery drill excludes "
         "concurrent load, antivirus interference and slow storage. The learned engines train on "
         "synthetic data by construction, so their results are a model-versus-rules comparison under "
         "controlled conditions, not a claim about field accuracy."),
        ("h2", "8.3 Future work"),
        ("p",
         "Four directions follow from the limitations. The first is closing the media blind "
         "spot without giving up the safety bar: magic-byte validation would recognise a JPEG "
         "whose header survives an in-place overwrite, partial-encryption detection would "
         "exploit the entropy gradient that section analysis only partly captures, and size or "
         "modification-pattern anomalies would add signals that do not depend on entropy at "
         "all."),
        ("p",
         "The second is moving enforcement out of user space: a minifilter driver on Windows or an eBPF "
         "sensor on Linux would place the observation point where a process cannot avoid it and block a "
         "write before the plaintext is destroyed. The third is turning the exchange into a real network "
         "with signed node identities and periodic digest anchoring. The fourth is operational: "
         "replacing the synthetic training set with data captured from the laboratory's own runs and "
         "extending it with YARA rules for ransom notes."),
        ("h1", "9. Conclusion"),
        ("p",
         "This project set out to build a ransomware defence that reacts to the statistical fingerprint "
         "the attack cannot avoid, and to prove with measurements that the reaction is fast, safe and "
         "auditable. The result is a working laboratory of roughly seventeen thousand lines of Python in "
         "which monitoring, entropy analysis, multi-signal decision making, campaign escalation, "
         "verified containment, strict-clean recovery, forensic reporting, ledger anchoring and "
         "federated fingerprint sharing operate as one pipeline, started with a single command and "
         "exercised by a deterministic measurement harness."),
        ("p",
         "The measured results are specific and honest. Against a live simulated WannaCry attack the "
         "system terminates the attacker at the second of eighteen files in 2.7 seconds, leaves no "
         "ransomware-suffixed file on disk, and returns all eighteen files byte-for-byte. Across the "
         "deterministic battery the default rule engine detects 87.5 per cent of attacked runs at a "
         "median of one to two file operations with zero false quarantines, while the opt-in Random "
         "Forest detects every tested scenario at the cost of six false quarantines on media workloads. "
         "The recovery drill recovers 45.1 per cent of attacked files and reports the remainder as "
         "contained or lost instead of omitting them, and the exchange simulation shows a node with no "
         "local history quarantining a locally ambiguous payload on the corroboration of two independent "
         "nodes."),
        ("p",
         "The most useful lesson from the failures is that composition beats tuning. The signals that "
         "produced the largest improvements were not sharper thresholds but additional, independent "
         "evidence — a second file confirming a campaign, a second node confirming a fingerprint, a "
         "content hash confirming that a file differs from its last clean state. Each mechanism is "
         "simple on its own, each converted a class of ambiguity into a decision, and the cases that "
         "remain undetected are precisely those where no additional evidence exists."),
        ("h1", "References"),
        ("refs", [
            "C. E. Shannon, “A Mathematical Theory of Communication,” Bell System Technical Journal, vol. 27, no. 3, pp. 379–423, 1948.",
            "A. L. Young and M. Yung, “Cryptovirology: Extortion-Based Security Threats and Countermeasures,” Proc. IEEE Symposium on Security and Privacy, 1996, pp. 129–140.",
            "L. Breiman, “Random Forests,” Machine Learning, vol. 45, no. 1, pp. 5–32, 2001.",
            "S. M. Lundberg and S.-I. Lee, “A Unified Approach to Interpreting Model Predictions,” Advances in Neural Information Processing Systems 30, 2017.",
            "National Institute of Standards and Technology, “SHA-3 Standard: Permutation-Based Hash and Extendable-Output Functions,” FIPS PUB 202, 2015.",
            "MITRE Corporation, “ATT&CK Technique T1486: Data Encrypted for Impact,” MITRE ATT&CK knowledge base.",
            "Watchdog — file system event monitoring for Python. https://pypi.org/project/watchdog/",
            "Flask and Flask-SocketIO — web framework and real-time transport. https://flask.palletsprojects.com/ · https://flask-socketio.readthedocs.io/",
            "scikit-learn — https://scikit-learn.org/ · SHAP — https://shap.readthedocs.io/ · web3.py — https://web3py.readthedocs.io/",
            "ENTROPY repository documentation: docs/architecture.md, docs/benchmark-report.md, docs/recovery-drill-report.md, docs/federated-exchange.md, docs/limitations.md.",
        ]),
        ("h1", "Appendix B. Reproduction Guide"),
        ("code",
         "# 1. Environment\n"
         "python -m venv .venv && source .venv/bin/activate\n"
         "pip install -r requirements.txt                     # pinned, resolution-safe set\n"
         "\n"
         "# 2. Install-time setup (creates the quarantine folder) and fixtures\n"
         "python install.py\n"
         "python victim_server/create_fake_files.py --clean   # deterministic 18-file estate\n"
         "\n"
         "# 3. Automated suite and measurements\n"
         "python -m unittest discover -s tests -v\n"
         "python -m benchmark                     # detection battery: 8 attacks + 7 workloads\n"
         "python -m benchmark.recovery_drill      # byte-for-byte recovery and RTO\n"
         "python -m benchmark.exchange_simulation # four-tenant federated sharing\n"
         "\n"
         "# 4. Live demonstration and report artefacts\n"
         "python lab.py                           # then open ports 5000, 5001 and 8001\n"
         "python report/figures/make_figures.py   # regenerate the figures used here\n"
         "python report/build_report.py           # rebuild this document"),
    ]

    return b
