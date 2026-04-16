#!/bin/bash
# Monitor Phase 17 Subagent Progress

echo "=== Phase 17 Subagent Monitor ==="
echo "Date: $(date)"
echo ""

# Check subagent output files
echo "Subagent Status:"
echo "----------------"

TASK_DIR="/var/folders/34/dhxjt7_11lb_442p39srwl480000gn/T/claude/-Volumes-ex-ssd-home-projects-python-vkg-solidity-true-vkg/tasks"

for agent_id in ab20226 a0b6dec ad4ca4f a7f4a11; do
    output_file="${TASK_DIR}/${agent_id}.output"

    if [ -f "$output_file" ]; then
        echo "Agent $agent_id:"
        # Show last 5 lines
        tail -n 5 "$output_file" | sed 's/^/  /'
        echo ""
    else
        echo "Agent $agent_id: No output file yet"
        echo ""
    fi
done

# Check discovery logs
echo "Discovery Logs:"
echo "---------------"

for i in 1 2 3 4; do
    log_file=".vrs/discovery/subagent_${i}_log.yaml"

    if [ -f "$log_file" ]; then
        echo "Subagent $i:"
        # Show summary
        grep -E "(sources_processed|vulnerabilities_extracted|decisions)" "$log_file" | head -10 | sed 's/^/  /'
        echo ""
    else
        echo "Subagent $i: No log file yet"
        echo ""
    fi
done

echo "=== Monitor Complete ==="
