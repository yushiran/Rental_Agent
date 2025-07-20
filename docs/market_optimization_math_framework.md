# Multi-Agent Rental Market Optimization: Mathematical Framework

## 1. Problem Statement

We model the rental market as a multi-agent optimization problem, where each agent (tenant or landlord) is a function making decisions to maximize its own utility. The overall market goal is to achieve efficient allocation and high satisfaction for all participants.

## 2. Mathematical Formulation

### 2.1 Sets and Variables
- **Tenants:** $\mathcal{T} = \{t_1, t_2, ..., t_n\}$
- **Landlords:** $\mathcal{L} = \{l_1, l_2, ..., l_m\}$
- **Properties:** $\mathcal{P} = \{p_1, p_2, ..., p_k\}$
- **Market State:** $S_t$ at time $t$
- **Decision Variables:** $x_{ij} \in \{0,1\}$, 1 if tenant $t_i$ is matched to property $p_j$
- **Price:** $\pi_{ij}$, agreed rent between $t_i$ and $l(p_j)$

### 2.2 Agent Utility Functions
- **Tenant Utility:** $U_T(t_i, p_j, \pi_{ij})$
- **Landlord Utility:** $U_L(l(p_j), p_j, \pi_{ij})$

### 2.3 Agent as Function
Each agent is a function:
$$A_i: S_t \times I_i \rightarrow a_i$$
where $I_i$ is private info, $a_i$ is the action (bid, accept, reject, etc).

### 2.4 Market Objective
Maximize total utility:
$$
\max_{\mathcal{M}} \sum_{i=1}^{n}\sum_{j=1}^{k} x_{ij} \cdot (U_T(t_i, p_j, \pi_{ij}) + U_L(l(p_j), p_j, \pi_{ij}))
$$

### 2.5 Constraints
- Each tenant/property matched at most once:
  $$\sum_{j=1}^{k} x_{ij} \leq 1, \forall i$$
  $$\sum_{i=1}^{n} x_{ij} \leq 1, \forall j$$
- **Price Feasibility Constraints:**
  - Tenant budget constraint: $\pi_{ij} \leq B(t_i)$
  - Landlord acceptance constraint: $\pi_{ij} \geq R(l(p_j))$
  
  **Detailed Explanation:**
  
  - $\pi_{ij}$: The agreed rental price between tenant $t_i$ and property $p_j$
  - $B(t_i)$: Maximum budget (affordability limit) of tenant $t_i$
  - $R(l(p_j))$: Minimum acceptable rent (reservation price) of landlord $l$ who owns property $p_j$
  - $l(p_j)$: Function mapping property $p_j$ to its owner landlord
  
  **Economic Interpretation:**
  
  1. **Upper Bound ($\pi_{ij} \leq B(t_i)$):** 
     - The rent cannot exceed what the tenant can afford
     - Example: If tenant John has max budget £2000/month, then $\pi_{John,apartment} \leq £2000$
  
  2. **Lower Bound ($\pi_{ij} \geq R(l(p_j))$):**
     - The rent must meet landlord's minimum expectations
     - Example: If landlord Mary won't accept less than £1500/month for her flat, then $\pi_{tenant,Mary's\_flat} \geq £1500$
  
  **Market Viability:**
  - A match is only possible if: $R(l(p_j)) \leq \pi_{ij} \leq B(t_i)$
  - This requires: $R(l(p_j)) \leq B(t_i)$ (bargaining zone exists)
  - If $R(l(p_j)) > B(t_i)$, no deal is possible between this tenant-property pair

**Code Implementation Example:**
  
  ```python
  def check_price_feasibility(tenant, property, proposed_price):
      """Check if proposed price satisfies both constraints"""
      tenant_budget = tenant.max_budget  # B(t_i)
      landlord_min_price = property.landlord.min_acceptable_rent  # R(l(p_j))
      
      # Check upper bound: tenant affordability
      if proposed_price > tenant_budget:
          return False, f"Price £{proposed_price} exceeds tenant budget £{tenant_budget}"
      
      # Check lower bound: landlord acceptance
      if proposed_price < landlord_min_price:
          return False, f"Price £{proposed_price} below landlord minimum £{landlord_min_price}"
      
      return True, "Price is feasible for both parties"
  
  def find_bargaining_zone(tenant, property):
      """Find the valid price range for negotiation"""
      B_ti = tenant.max_budget
      R_lpj = property.landlord.min_acceptable_rent
      
      if R_lpj <= B_ti:
          return (R_lpj, B_ti), "Bargaining zone exists"
      else:
          return None, "No viable price range - deal impossible"
  
  # Example usage:
  tenant_john = Tenant(max_budget=2000)
  landlord_mary = Landlord(min_acceptable_rent=1500)
  property_flat = Property(landlord=landlord_mary)
  
  zone, message = find_bargaining_zone(tenant_john, property_flat)
  print(f"Valid price range: £{zone[0]} - £{zone[1]}")  # £1500 - £2000
  ```

## 3. LangGraph as Optimizer
The LangGraph workflow is an iterative solver for this optimization:
- **Matching phase:** Propose matches
- **Negotiation phase:** Agents negotiate price and terms
- **Update state:** Accept/reject, update market state
- **Repeat until convergence**

## 4. Evaluation Metrics

### 4.1 Market Efficiency
$$E = \frac{\text{Total Achieved Utility}}{\text{Theoretical Maximum Utility}}$$

**Parameter Definitions:**
- $E$: Market efficiency ratio (0 ≤ E ≤ 1)
- $\text{Total Achieved Utility}$: Sum of actual utilities obtained by all matched agents
- $\text{Theoretical Maximum Utility}$: Optimal utility achievable under perfect information and matching

**Economic Interpretation:**
- E = 1: Perfect efficiency (optimal allocation achieved)
- E = 0: Complete inefficiency (no value created)
- Higher E indicates better market performance

**Calculation Example:**
```python
def calculate_market_efficiency(achieved_matches, optimal_matches):
    achieved_utility = sum(tenant_utility + landlord_utility 
                          for tenant_utility, landlord_utility in achieved_matches)
    optimal_utility = sum(tenant_utility + landlord_utility 
                         for tenant_utility, landlord_utility in optimal_matches)
    return achieved_utility / optimal_utility if optimal_utility > 0 else 0
```

### 4.2 Price Equilibrium
$$PE = 1 - \frac{\sigma(\pi)}{\overline{\pi}}$$

**Parameter Definitions:**
- $PE$: Price equilibrium index (0 ≤ PE ≤ 1)
- $\sigma(\pi)$: Standard deviation of all agreed rental prices
- $\overline{\pi}$: Mean of all agreed rental prices
- $\pi = \{\pi_{ij} | x_{ij} = 1\}$: Set of all successful rental prices

**Economic Interpretation:**
- PE = 1: Perfect price stability (all properties rent at same price)
- PE = 0: Maximum price volatility (prices highly dispersed)
- Higher PE indicates more stable, equilibrium-like pricing

**Calculation Example:**
```python
import numpy as np

def calculate_price_equilibrium(rental_prices):
    if len(rental_prices) == 0:
        return 0
    mean_price = np.mean(rental_prices)
    std_price = np.std(rental_prices)
    return 1 - (std_price / mean_price) if mean_price > 0 else 0
```

### 4.3 Match Quality
$$Q = \frac{1}{|\mathcal{M}|} \sum_{(t_i,p_j) \in \mathcal{M}} \text{sim}(t_i, p_j)$$

**Parameter Definitions:**
- $Q$: Average match quality score (0 ≤ Q ≤ 1)
- $|\mathcal{M}|$: Total number of successful matches
- $\mathcal{M}$: Set of all successful tenant-property pairs
- $\text{sim}(t_i, p_j)$: Similarity/compatibility score between tenant $t_i$ and property $p_j$

**Similarity Function Components:**
- Location preference alignment
- Budget vs. rent compatibility
- Property features vs. tenant requirements
- Lifestyle compatibility

**Calculation Example:**
```python
def calculate_similarity(tenant, property):
    # Location compatibility (0-1)
    location_score = 1 - distance(tenant.preferred_location, property.location) / max_distance
    
    # Budget compatibility (0-1)
    budget_score = min(tenant.budget / property.rent, 1.0)
    
    # Feature compatibility (0-1)
    feature_score = len(set(tenant.required_features) & set(property.features)) / len(tenant.required_features)
    
    # Weighted average
    return 0.4 * location_score + 0.3 * budget_score + 0.3 * feature_score

def calculate_match_quality(successful_matches):
    if len(successful_matches) == 0:
        return 0
    total_similarity = sum(calculate_similarity(tenant, property) 
                          for tenant, property in successful_matches)
    return total_similarity / len(successful_matches)
```

### 4.4 Negotiation Rounds
$$R = \frac{1}{|\mathcal{M}|} \sum_{(t_i,p_j) \in \mathcal{M}} r_{ij}$$

**Parameter Definitions:**
- $R$: Average number of negotiation rounds per successful match
- $|\mathcal{M}|$: Total number of successful matches
- $r_{ij}$: Number of negotiation rounds required for tenant $t_i$ and property $p_j$ to reach agreement

**Efficiency Interpretation:**
- Lower R: More efficient negotiations (faster agreements)
- Higher R: More complex negotiations (longer bargaining process)
- Optimal R depends on market complexity and agent sophistication

**Calculation Example:**
```python
def calculate_negotiation_rounds(negotiation_history):
    successful_matches = [match for match in negotiation_history if match.status == "agreed"]
    if len(successful_matches) == 0:
        return 0
    total_rounds = sum(match.num_rounds for match in successful_matches)
    return total_rounds / len(successful_matches)
```

### 4.5 Overall Satisfaction
$$S = \alpha S_T + (1-\alpha) S_L$$

**Parameter Definitions:**
- $S$: Overall market satisfaction (0 ≤ S ≤ 1)
- $S_T$: Average tenant satisfaction across all tenants
- $S_L$: Average landlord satisfaction across all landlords
- $\alpha$: Weighting parameter (0 ≤ α ≤ 1), typically α = 0.5 for equal weighting

**Satisfaction Components:**
- **Tenant Satisfaction:** $S_T = \frac{1}{n} \sum_{i=1}^{n} s_T(t_i)$
- **Landlord Satisfaction:** $S_L = \frac{1}{m} \sum_{i=1}^{m} s_L(l_i)$

**Individual Satisfaction Functions:**
```python
def tenant_satisfaction(tenant, matched_property, agreed_price):
    if matched_property is None:
        return 0  # No match found
    
    # Price satisfaction (lower rent = higher satisfaction)
    price_sat = (tenant.budget - agreed_price) / tenant.budget
    
    # Property satisfaction (features, location)
    property_sat = calculate_similarity(tenant, matched_property)
    
    return 0.6 * price_sat + 0.4 * property_sat

def landlord_satisfaction(landlord, matched_tenant, agreed_price):
    if matched_tenant is None:
        return 0  # No match found
    
    # Price satisfaction (higher rent = higher satisfaction)
    price_sat = (agreed_price - landlord.min_rent) / (landlord.target_rent - landlord.min_rent)
    
    # Tenant quality satisfaction
    tenant_quality = evaluate_tenant_quality(matched_tenant)
    
    return 0.7 * price_sat + 0.3 * tenant_quality

def calculate_overall_satisfaction(tenants, landlords, alpha=0.5):
    tenant_satisfactions = [tenant_satisfaction(t, t.matched_property, t.agreed_price) 
                           for t in tenants]
    landlord_satisfactions = [landlord_satisfaction(l, l.matched_tenant, l.agreed_price) 
                             for l in landlords]
    
    S_T = np.mean(tenant_satisfactions)
    S_L = np.mean(landlord_satisfactions)
    
    return alpha * S_T + (1 - alpha) * S_L
```

**Weighting Parameter Guidelines:**
- α = 0.5: Equal importance to both tenant and landlord satisfaction
- α > 0.5: Tenant-favorable market analysis
- α < 0.5: Landlord-favorable market analysis

## 5. Research Directions
- Optimal matching algorithms
- Negotiation strategy analysis
- Information asymmetry effects
- Dynamic pricing
- Multi-objective optimization

## 6. Experimental Design
- Compare different agent strategies (random, preference-based, adaptive)
- Vary information access (symmetric/asymmetric)
- Measure efficiency, satisfaction, convergence speed

## 7. Conclusion
This framework provides a rigorous mathematical foundation for analyzing and optimizing multi-agent rental markets using your LangGraph-based system. It enables systematic experimentation and benchmarking for academic research.
