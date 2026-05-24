# env/dynamics.py
import random

def spread_fires(model):
    W, H = model.width, model.height
    new_fires = []
    extinguished = 0

    # ULTRA-CONSERVATIVE fire spread - each fire has only small chance to spread at all
    existing_fires = []
    for y in range(H):
        for x in range(W):
            if model.cell_types[y][x] == "fire":
                existing_fires.append((x, y))
    
    # Only let a small fraction of fires spread each tick  
    max_spreading_fires = max(1, len(existing_fires) // 5)  # At most 20% of fires spread (increased from 10%)
    spreading_fires = random.sample(existing_fires, min(max_spreading_fires, len(existing_fires)))
    
    for x, y in spreading_fires:
        # Each spreading fire only tries ONE random direction
        directions = [(1,0),(-1,0),(0,1),(0,-1)]
        dx, dy = random.choice(directions)
        nx, ny = x+dx, y+dy
        
        if 0 <= nx < W and 0 <= ny < H:
            ct = model.cell_types[ny][nx]
            # Only spread to buildings and roads, with low probability
            if ct in ("building", "road") and random.random() < model.p_fire_spread:
                # Don't spread to occupied cells
                cell_contents = model.grid.get_cell_list_contents([(nx, ny)])
                has_agents = any(not hasattr(agent, 'cell_type') for agent in cell_contents)
                if not has_agents and (nx, ny) not in new_fires:
                    new_fires.append((nx, ny))
    
    # FIXED: Use the new fire agent system
    for (x,y) in new_fires:
        model.add_fire_at(x, y)
    
    return {"extinguished": extinguished}

def trigger_aftershocks(model):
    """Enhanced aftershocks - randomly create rubble or fires at moderate intervals."""
    W, H = model.width, model.height
    roads_cleared = 0
    
    # Moderate aftershock probability - not too frequent but noticeable
    if random.random() < model.p_aftershock:
        # Choose random location
        x = random.randrange(W)
        y = random.randrange(H)
        cell_type = model.cell_types[y][x]
        
        # 70% chance for rubble, 30% chance for fire (rubble more common)
        if random.random() < 0.7:
            # Create rubble - can affect roads and buildings
            if cell_type in ("road", "building") and cell_type != "rubble":
                # Add rubble environment agent for visualization (this will also set cell type)
                model.add_rubble_at(x, y)
                print(f"💥 Aftershock created rubble at ({x}, {y})")
        else:
            # Create fire - can affect buildings and roads
            if cell_type in ("road", "building") and cell_type not in ("fire", "rubble"):
                model.add_fire_at(x, y)
                print(f"🔥 Aftershock started fire at ({x}, {y})")
    
    return {"roads_cleared": roads_cleared}
