ALTER TABLE order
ADD CONSTRAINT order_customer_id_fkey FOREIGN KEY (customer_id)
REFERENCES customer(id) NOT VALID;
-- Fast, doesn’t scan

ALTER TABLE order VALIDATE CONSTRAINT order_customer_id_fkey;
-- Slow scan, but you can run it off-peak


-- The subtlety in Django

-- Django forces you to either:

-- null=True → fast column add, but still triggers constraint validation scan.

-- Or give a default → full table rewrite + constraint validation.

-- So null=True avoids a rewrite, but not the validation scan.
