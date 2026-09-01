# Formal addendum: feature-level CCD

Let each endpoint be affine over one normalized step, `x(t)=x0+t(x1-x0)`. A vertex–face contact requires both coplanarity and closed-triangle containment. The signed tetrahedral volume is cubic because it is the scalar triple product of three affine vectors. Edge–edge coplanarity is cubic for the same reason.

The algebraic candidate set is necessary but not sufficient: every root must be subjected to a geometric witness test. Conversely, when the cubic is identically zero, roots no longer enumerate the contact set; the features are persistently coplanar. The solver therefore changes proof technique rather than pretending the polynomial has an ordinary finite root set.

For moving sets `A(t)` and `B(t)`, the separation distance is Lipschitz when their point velocities are bounded. If every point of `A` moves at speed no more than `VA` and every point of `B` at speed no more than `VB`, then

`|d(A(t1),B(t1)) - d(A(t0),B(t0))| ≤ (VA+VB)|t1-t0|`.

For an affine triangle, every interior point velocity is a convex combination of its vertex velocities, so the maximum vertex speed is a valid set-speed bound. For a segment, the maximum endpoint speed is valid. This justifies the fallback interval-pruning rule.

A floating-point result remains conditional on scaling, root conditioning, and tolerance. Exactness is therefore a future conformance level, not assumed by notation.
