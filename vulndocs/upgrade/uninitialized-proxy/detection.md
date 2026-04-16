# Uninitialized Proxy Detection

## Overview
Identify implementation contracts vulnerable to initialization attacks.

## Key Signals
- Missing `_disableInitializers()` in constructor
- No initializer modifier on setup function
- Implementation deployed without immediate initialization
