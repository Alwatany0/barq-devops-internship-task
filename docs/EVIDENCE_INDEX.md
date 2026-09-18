# Evidence and Submission Index

## Submission fields

- Repository URL: https://github.com/Alwatany0/barq-devops-internship-task
- Final commit: TBD after final commit
- Matching CI run: TBD after push
- Continuous 12-18 minute video URL: TBD
- Challenge receipt ID: Not generated; the recorded challenge attempt stopped during preflight
- Starting video commit: b72e8e7
- Later documentation-only commits: TBD, if any

## Requirement evidence

| Requirement | File / output | Commit | Video timestamp |
|---|---|---|---|
| Repository, starting commit and clean status | git status, git log | b72e8e7 baseline | TBD |
| Docker services and health | docker-compose.yml, docker compose ps | final technical commit | TBD |
| Required endpoints | HTTP endpoint checks | final technical commit | TBD |
| Three backend instances | docker-compose.yml, nginx/nginx.conf, /instance output | final technical commit | TBD |
| Failure and recovery | failure_test.py and test output | final technical commit | TBD |
| PostgreSQL persistence | /records before/after recreation | d395439 + final state | TBD |
| PostgreSQL backup/restore | backup.sh, restore.sh | fed0147, d395439 | TBD |
| Historical log analysis | log_analysis.md and logs/ | existing documentation commits | TBD |
| Validation automation | validate.py and VALIDATION PASSED | final technical commit | TBD |
| CI automation | .github/workflows/ci.yml | final technical commit | TBD |
| Security review | security_review.md | final documentation commit | TBD |
| Technical decisions | decisions.md | final documentation commit | TBD |
| AI disclosure | AI_USAGE.md | final documentation commit | TBD |
| Final architecture | architecture.png, docs/ARCHITECTURE.md | final documentation commit | TBD |
| Public port 8090 | .env.example, .github/workflows/ci.yml, docker-compose.yml | final technical commit | TBD |

## Final architecture

The final repository state is three Flask application instances behind NGINX on public port 8090. The internal Flask port remains 8080.

## Challenge evidence limitation

./video_challenge.sh was attempted during the recording, but its preflight stopped before the challenge fault was injected. No challenge receipt was generated. The challenge was not reset or rerun.

## Evidence integrity

Commit hashes, CI runs, video timestamps and challenge receipt information will be filled with the actual values after they exist. No fabricated dates, hashes, timestamps or test results are used.
