---
name: plan-feature
description: Plan new features for openstack-k8s-operators operators following best practices and architectural patterns
user-invocable: true
allowed-tools: ["Read", "Grep", "Glob", "TodoWrite"]
---

# Plan Feature

This skill helps plan new features for openstack-k8s-operators operators by:

1. **Architecture Analysis**: Understanding existing operator structure
2. **Best Practice Alignment**: Following controller-runtime patterns
3. **Impact Assessment**: Identifying affected components
4. **Implementation Planning**: Breaking down work into manageable tasks

## Planning Process

When planning a new feature:

1. **Analyze Current Architecture**
   - Review existing controllers and CRDs
   - Understand current reconciliation patterns
   - Identify reusable components

2. **Design Considerations**
   - CRD schema design and validation
   - Controller logic and reconciliation strategy
   - Status conditions and observability
   - Backwards compatibility

3. **Implementation Strategy**
   - Break down into phases
   - Identify dependencies
   - Plan testing approach
   - Consider migration paths

4. **Create Action Items**
   - Use TodoWrite to create structured tasks
   - Prioritize implementation order
   - Include testing and documentation

## Architectural Patterns

Follow these openstack-k8s-operators patterns:
- Operator SDK structure
- Custom Resource Definitions with proper validation
- Controller reconciliation with proper error handling
- Status conditions following Kubernetes conventions
- Proper RBAC and security considerations