Work plan: Let's initialize git for versioning. For now, we will do part (2) first. We will use the maps/example_map.txt as the test bed for our solver. With 13 walls, the optimal solution has a score of 103.

(1) Reading in the problem.  
Parse a png input image (here, we'll test with 'images/example.png') into a 2d matrix, with integer values for each element identified:
(0) water tile
(1) grass tile
(2) horse tile

the input image is shifted and probably has a border, so we need to identify the grid that underpins the image

We should test the parser against the maps/example_map.txt to check for correctness: there the water tiles are represented by "~", the ground tiles by ".", and the horse by "H".

We should then create an adjacency graph for edge-edge neighbours consisting of grass tiles. 

(2) Solving. The problem. 

The game is played by placing a finite number of walls into empty grass tiles. When all the walls are placed, the area enclosed by the placed walls and by the water tiles must contain the horse. Each tile inside enclosed by those walls and water tiles is converted into pasture, and scores a point.

We want to express the horse enclosure game as a integer linear programming problem, and optimize for the number of pasture. Therefore, for every tile x not occupied by the horse or by a water tile we will introduce the following binary variables: b_g(x), b_p(x), b_w(x), which correspond to that tile being assigned at the end of the game to a grass tile, a pasture tile, or a wall tile.

==========
Expressing the integer linear programming problem:  
==========

Objective:
maximize 1+sum_x b_p(x)

Note, the +1 comes from the fact that the horse is always scored as a point, but that it will not have a corresponding set of assignment variables. 

==========

Constraints: For conciseness, I will omit the (x) on all of the tile variables.

Each tile must be exactly one of  b_g, b_p, b_w.
2 > b_g+b_p+b_w > 0

Tiles at the boundary must be either grass or wall. Such tiles have the additional constraint:
b_w = 0

Tiles adjacent to the horse cannot be grass tiles: 
b_g = 0

Adjacent tiles x, x' must both be the same state, or at least one of them must be walls. We will introduce an auxilliary binary variable z(x,x') that expresses whether the two tiles are the same state (b_g(x) == b_g(x') || b_p(x) == b_p(x')). Therefore we have the constraint for every pair of adjacent tiles x,x': 
b_w(x) + b_w(x') + z(x,x') > 0

where the auxilliary variable z(x,x') == z_p(x,x') || z_g(x,x'):
z(x,x') - z_p(x,x') - z_g(x,x') = 0

and we introduce the auxilliary variables z_p and z_g to capture whether both x, x' are pasture and grass respectively. The z_p constraint is then: 
z_p(x,x') <= b_p(x)
z_p(x,x') <= b_p(x')
z_p(x,x') >= b_p(x) + b_p(x') - 1

and similarly the z_g(x,x') constraint is then:
z_g(x,x') <= b_g(x)
z_g(x,x') <= b_g(x')
z_g(x,x') >= b_g(x) + b_g(x') - 1

maximum number of walls constraint: 
sum_x b_w(x) <= MAX_WALLS

where MAX_WALLS is a user provided constraint. To start, we should set it to 13. 

==========

Once the ILP is fully expressed, we should solve it using PULP, and return the assignment of variables. We should print out the solution score, and then plot the resulting solution using matplotlib. Each grass tile should be plotted with green, water tiles with blue, the horse with brown, and the wall tiles in light grey. A fine grid (lw = 0.5) should be plotted to aid in the visualization of the grid positions.
