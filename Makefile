CC = gcc
PYTHON ?= python3
OPT ?= O2
BASE_FLAGS = -std=c11 -Wall -Wextra -Wpedantic -Werror -fno-lto
CFLAGS = $(BASE_FLAGS) -$(OPT)
BUILD = build/$(OPT)
CORE = $(BUILD)/branchy.o $(BUILD)/masked.o $(BUILD)/support.o
TRACED = $(BUILD)/branchy_trace.o $(BUILD)/masked_trace.o
RUN = $(PYTHON) scripts/lab.py --opt $(OPT) --cc '$(CC)' --flags '$(CFLAGS)'

.NOTPARALLEL:
.PHONY: all binaries test trace bench inspect sanitize report FORCE
all:
	$(MAKE) OPT=O2 test trace bench
	$(MAKE) OPT=O3 test bench
	$(MAKE) OPT=O2 inspect sanitize report
binaries: $(BUILD)/test $(BUILD)/trace $(BUILD)/bench

$(BUILD):
	mkdir -p $@
$(BUILD)/config: FORCE | $(BUILD)
	@$(PYTHON) scripts/build_config.py '$@' '$(CC)' '$(CFLAGS)'
$(BUILD)/%.o: src/%.c src/gf2.h Makefile $(BUILD)/config | $(BUILD)
	$(CC) $(CFLAGS) -c $< -o $@
$(BUILD)/%_trace.o: src/%.c src/gf2.h Makefile $(BUILD)/config | $(BUILD)
	$(CC) $(CFLAGS) -DGF2_TRACE -c $< -o $@
$(BUILD)/test: $(BUILD)/test.o $(CORE) $(TRACED)
	$(CC) $(CFLAGS) $^ -o $@
$(BUILD)/trace: $(BUILD)/trace.o $(CORE) $(TRACED)
	$(CC) $(CFLAGS) $^ -o $@
$(BUILD)/bench: $(BUILD)/bench.o $(CORE)
	$(CC) $(CFLAGS) $^ -o $@

test: $(BUILD)/test
	$(RUN) test
trace: $(BUILD)/trace
	$(RUN) trace
bench: $(BUILD)/bench
	$(RUN) bench
inspect:
	$(MAKE) OPT=O2 binaries
	$(MAKE) OPT=O3 binaries
	$(RUN) inspect
sanitize:
	$(RUN) sanitize
report:
	$(RUN) report

# No clean target: previous raw observations are useful research evidence.
